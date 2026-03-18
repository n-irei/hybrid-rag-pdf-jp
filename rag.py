"""
FX PDF RAG システム
使用前に以下を実行:
pip install langchain langchain-community langchain-ollama langchain-chroma chromadb pymupdf anthropic

Ollamaが起動済みで以下のモデルがインストール済みであること:
  ollama pull nomic-embed-text

環境変数:
  ANTHROPIC_API_KEY  （PDFテキスト抽出 + 回答生成に使用）
"""

import os
import base64
import fitz  # pymupdf
import anthropic

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# ── 設定 ──────────────────────────────────────────────
PDF_PATH        = os.path.join(os.path.dirname(__file__), "FXで成功するための秘訣.pdf")
CHROMA_DIR      = os.path.join(os.path.dirname(__file__), "chroma_db")
CLAUDE_MODEL    = "claude-haiku-4-5"  # LLM（回答生成）
EMBEDDING_MODEL = "nomic-embed-text"  # 埋め込みモデル
# ────────────────────────────────────────────────────

PROMPT_TEMPLATE = """あなたはFX（外国為替取引）の専門家です。
以下のコンテキストを参考に、質問に日本語で答えてください。
コンテキストに答えがない場合は「資料には記載がありません」と答えてください。

コンテキスト:
{context}

質問: {question}

回答:"""


def page_to_png_base64(page: fitz.Page, dpi: int = 150) -> str:
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return base64.standard_b64encode(pix.tobytes("png")).decode("utf-8")


def extract_text_with_vision(image_b64: str, client: anthropic.Anthropic) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "この画像に書かれているテキストをすべて正確に抽出してください。"
                        "レイアウトや改行をできるだけ保持し、画像の説明は不要です。"
                        "テキストのみを出力してください。"
                    ),
                },
            ],
        }],
    )
    return response.content[0].text.strip()


def load_pdf(pdf_path: str) -> list[Document]:
    pdf = fitz.open(pdf_path)
    total_pages = len(pdf)

    # Step1: fitz でテキスト抽出
    fitz_texts = [page.get_text().strip() for page in pdf]
    total_chars = sum(len(t) for t in fitz_texts)

    if total_chars > 0:
        pdf.close()
        return [
            Document(page_content=text, metadata={"source": pdf_path, "page": i})
            for i, text in enumerate(fitz_texts) if text
        ]

    # Step2: Anthropic Vision API でOCR
    print("画像ベースPDFのため Vision API でテキスト抽出します...")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("環境変数 ANTHROPIC_API_KEY が設定されていません")

    vision_client = anthropic.Anthropic(api_key=api_key)
    documents = []

    for i, page in enumerate(pdf):
        print(f"  Page {i+1}/{total_pages} 処理中...", end=" ", flush=True)
        image_b64 = page_to_png_base64(page)
        text = extract_text_with_vision(image_b64, vision_client)
        print(f"{len(text)} 文字")
        if text:
            documents.append(Document(
                page_content=text,
                metadata={"source": pdf_path, "page": i},
            ))

    pdf.close()
    return documents


def build_vectorstore() -> Chroma:
    print(f"PDFを読み込み中: {PDF_PATH}")
    docs = load_pdf(PDF_PATH)

    if not docs:
        raise RuntimeError("PDFからテキストを抽出できませんでした。")
    print(f"{len(docs)} ページのテキストを取得")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", "、", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"{len(chunks)} チャンクに分割")

    print("埋め込みベクトルを生成中...")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    print("ベクトルDB構築完了")
    return vectorstore


def load_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)


def main():
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        print("既存のベクトルDBを読み込み中...")
        vectorstore = load_vectorstore()
    else:
        vectorstore = build_vectorstore()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("環境変数 ANTHROPIC_API_KEY が設定されていません")
    claude_client = anthropic.Anthropic(api_key=api_key)

    def call_claude(prompt_value) -> str:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt_value.text}],
        )
        return response.content[0].text

    llm = RunnableLambda(call_claude)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
    )

    print("\n" + "="*50)
    print("FX RAG システム起動 （終了: quit または exit）")
    print("="*50)

    while True:
        try:
            query = input("\n質問: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n終了します。")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("終了します。")
            break

        print("考え中...")
        answer = chain.invoke(query)
        print(f"\n回答:\n{answer}")

        sources = retriever.invoke(query)
        if sources:
            pages = sorted({doc.metadata.get("page", 0) + 1 for doc in sources
                            if isinstance(doc.metadata.get("page"), int)})
            print(f"\n（参照ページ: {pages}）")


if __name__ == "__main__":
    main()
