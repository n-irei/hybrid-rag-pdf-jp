# hybrid-rag-pdf-jp

日本語PDFに対応したハイブリッドRAG（検索拡張生成）システムです。
PDFをClaude Vision APIでテキスト抽出し、ChromaDB + nomic-embed-text でベクトル検索、Claude APIで日本語回答を生成します。

---

## 技術スタック

| コンポーネント | 役割 |
|---|---|
| [LangChain](https://www.langchain.com/) | RAGパイプライン構築 |
| [ChromaDB](https://www.trychroma.com/) | ローカルベクトルデータベース |
| [nomic-embed-text](https://ollama.com/library/nomic-embed-text) | テキスト埋め込み（Ollama経由） |
| [Claude API](https://www.anthropic.com/) | Vision OCR・回答生成 |
| [Ollama](https://ollama.com/) | ローカル埋め込みモデルの実行環境 |

---

## システム構成

```
PDF ファイル
    │
    ▼
Claude Vision API（claude-opus-4-6）
    │  画像ベースPDFのOCR・テキスト抽出
    ▼
テキスト分割（RecursiveCharacterTextSplitter）
    │
    ▼
nomic-embed-text（Ollama）
    │  埋め込みベクトル生成
    ▼
ChromaDB（ローカル永続化）
    │  類似チャンク検索（k=4）
    ▼
Claude API（claude-haiku-4-5）
    │  コンテキストを元に日本語で回答生成
    ▼
回答出力
```

> テキストが直接抽出できるPDFは Vision API をスキップし、PyMuPDF で高速処理します。

---

## セットアップ手順

### 1. 前提条件

- **Python 3.11** 以上
- **Ollama** がインストール・起動済みであること
- **Anthropic API キー** を取得済みであること

### 2. Ollama のセットアップ

[Ollama 公式サイト](https://ollama.com/)からインストール後、埋め込みモデルを取得します。

```bash
ollama pull nomic-embed-text
```

### 3. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、APIキーを設定します。

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

または、シェルで直接設定します。

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

### 4. 依存パッケージのインストール

```bash
pip install langchain langchain-community langchain-ollama langchain-chroma chromadb pymupdf anthropic
```

### 5. PDFファイルの配置

RAG 対象の PDF ファイルをプロジェクトルートに配置し、`rag.py` の `PDF_PATH` を設定します。

```python
PDF_PATH = os.path.join(os.path.dirname(__file__), "your_document.pdf")
```

---

## 使い方

```bash
python rag.py
```

起動すると対話モードになります。

```
==================================================
FX RAG システム起動 （終了: quit または exit）
==================================================

質問: リスク管理の基本を教えてください
考え中...

回答:
リスク管理の基本は...

（参照ページ: [3, 7, 12]）

質問: quit
終了します。
```

### 動作の詳細

| 状況 | 動作 |
|---|---|
| `chroma_db/` が存在しない | PDF を読み込みベクトルDBを新規構築 |
| `chroma_db/` が存在する | 既存DBを再利用（高速起動） |
| テキスト抽出可能なPDF | PyMuPDF で直接抽出（Vision APIを使用しない） |
| 画像ベースのPDF | Claude Vision API（claude-opus-4-6）でOCR処理 |

### ベクトルDBの再構築

PDFを更新した場合は `chroma_db/` ディレクトリを削除してから再実行してください。

```bash
rm -rf chroma_db/
python rag.py
```

---

## デモ動画

[![ハイブリッドRAGシステム デモ](https://img.youtube.com/vi/VVGUYLBhijE/0.jpg)](https://www.youtube.com/watch?v=VVGUYLBhijE)

---

## ライセンス

MIT
