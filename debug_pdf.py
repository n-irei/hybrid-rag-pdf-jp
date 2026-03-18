"""PDF読み込みデバッグスクリプト"""
import os

PDF_PATH = os.path.join(os.path.dirname(__file__), "FXで成功するための秘訣.pdf")

print("=" * 60)
print("【1】PyMuPDFLoader テスト")
print("=" * 60)
try:
    from langchain_community.document_loaders import PyMuPDFLoader
    loader = PyMuPDFLoader(PDF_PATH)
    docs = loader.load()
    print(f"ページ数: {len(docs)}")
    for i, doc in enumerate(docs):
        text = doc.page_content.strip()
        print(f"  Page {i+1}: {len(text)} 文字  先頭50文字→ {repr(text[:50])}")
except Exception as e:
    print(f"エラー: {e}")

print()
print("=" * 60)
print("【2】pymupdf (fitz) 直接読み込みテスト")
print("=" * 60)
try:
    import fitz  # PyMuPDF
    doc = fitz.open(PDF_PATH)
    print(f"ページ数: {len(doc)}")
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        print(f"  Page {i+1}: {len(text)} 文字  先頭50文字→ {repr(text[:50])}")
    doc.close()
except Exception as e:
    print(f"エラー: {e}")

print()
print("=" * 60)
print("【3】pdfplumber テスト")
print("=" * 60)
try:
    import pdfplumber
    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"ページ数: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").strip()
            print(f"  Page {i+1}: {len(text)} 文字  先頭50文字→ {repr(text[:50])}")
except ImportError:
    print("pdfplumber 未インストール → pip install pdfplumber")
except Exception as e:
    print(f"エラー: {e}")

print()
print("=" * 60)
print("【4】PDFファイル情報")
print("=" * 60)
try:
    import fitz
    doc = fitz.open(PDF_PATH)
    meta = doc.metadata
    print(f"  暗号化: {doc.is_encrypted}")
    print(f"  ページ数: {len(doc)}")
    print(f"  タイトル: {meta.get('title', 'なし')}")
    print(f"  作成者: {meta.get('creator', 'なし')}")
    # 画像ベースかどうか確認
    page = doc[0]
    blocks = page.get_text("blocks")
    images = page.get_images()
    print(f"  1ページ目 テキストブロック数: {len(blocks)}")
    print(f"  1ページ目 画像数: {len(images)}")
    if len(images) > 0 and len(blocks) == 0:
        print("  ★ 画像ベースPDF（スキャン）の可能性あり → OCRが必要")
    doc.close()
except Exception as e:
    print(f"エラー: {e}")
