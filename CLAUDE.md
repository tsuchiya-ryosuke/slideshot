# CLAUDE.md — SlideShot プロジェクト情報

## Gemini API モデル情報（2026年2月時点）

### 画像生成モデル

| モデル名 | 通称 | 特徴 | 状態 |
|---|---|---|---|
| `gemini-2.5-flash-image` | Nano Banana | 高速・大量処理向け | ✅ 現行 |
| `gemini-3-pro-image-preview` | Nano Banana Pro | 高品質・複雑な指示対応・Thinking付き | ✅ 現行 |
| `gemini-3.1-flash-image-preview` | Nano Banana 2 | 高速・高品質のバランス型（3 Proの後継） | ✅ 現行 |
| `gemini-3-pro-preview` | — | テキスト推論モデル | ⚠️ 2026-03-09 廃止予定 |
| `gemini-2.0-flash-preview-image-generation` | — | 旧世代の画像生成（実験的） | ❌ 旧世代 |

**現在 SlideShot で使用しているモデル: `gemini-3-pro-image-preview`**

> ⚠️ **重要: API・モデルを勝手に変更しないこと**
> 疎通確認済みの構成（SDK: `google-genai`、モデル: `gemini-3-pro-image-preview`）は動作確認済みです。
> 明示的な指示がない限り、API・SDK・モデル名を変更してはなりません。

### テキスト生成モデル（プロンプト生成用）

| モデル名 | 特徴 |
|---|---|
| `gemini-2.5-flash-lite` | 軽量・高速・低コスト。プロンプト生成に使用 |
| `gemini-2.5-flash` | 標準的な高性能モデル |
| `gemini-3-pro-preview` | 最高品質の推論（2026-03-09 廃止予定） |
| `gemini-3.1-pro-preview` | 3 Pro Previewの後継 |

---

### SDK

- **使用SDKは `google-genai`（新SDK）を使うこと**
- 旧SDK `google-generativeai` は**非推奨・廃止済み**であり使ってはならない

```python
# ✅ 正しいインポート
from google import genai
from google.genai import types

# ❌ 廃止済み（使わないこと）
# import google.generativeai as genai
```

---

### 画像生成 API の使い方

```python
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client(api_key="YOUR_API_KEY")

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="your prompt here",
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",   # スライド用は "16:9"
            image_size="2K",       # "512px" | "1K" | "2K" | "4K"
        ),
    ),
)

for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image = Image.open(BytesIO(part.inline_data.data))  # data は bytes（base64デコード不要）
        image.save("output.png")
```

#### `aspect_ratio` の選択肢
`"1:1"`, `"2:3"`, `"3:2"`, `"9:16"`, **`"16:9"`**, `"21:9"` など
スライド（横長）には `"16:9"` を使う。

#### `image_size` の選択肢
`"512px"`, `"1K"`, `"2K"`, `"4K"`

#### `response_modalities` の注意
- 値は **大文字**で指定: `"IMAGE"`, `"TEXT"`
- `GenerateContentConfig` を使う（旧 `GenerationConfig` は廃止）

---

### 料金（`gemini-3-pro-image-preview` / 2026年2月時点）

出力画像はトークン課金（$60 / 100万トークン）：

| 解像度 | トークン数 | 1枚あたりのコスト |
|---|---|---|
| 512px | 747 tokens | $0.045 |
| 1K | 1,120 tokens | $0.067 |
| 2K | 1,680 tokens | $0.101 |
| 4K | 2,520 tokens | $0.151 |

`gemini-2.5-flash-image` は $30 / 100万トークン（1枚 ≈ $0.039）でより安価。

---

---

## Claude へのルール（厳守）

### API・モデルを変更しないこと

- **画像生成モデルは `gemini-3-pro-image-preview` で固定**
- **プロンプト生成モデルは `gemini-2.5-flash-lite` で固定**
- 明示的な指示がない限り、モデル名・API エンドポイント・SDK を変更してはならない
- `google-genai` SDK を使い続けること（`google-generativeai` への差し戻し禁止）

---

## プロンプト精度・画像品質の改善方針

### 1. プロンプト生成精度を上げる

#### 1-1. システムプロンプトの強化
現在のプロンプト生成指示は汎用的。以下の要素を明示的に指示すると精度が上がる：

- **構図の指定**: 主役の配置（中央・左寄り・三分割など）
- **テキストスペースの確保**: "leave clean space in the upper-left for title text overlay"
- **スライド特有の制約**: 余白・テキスト干渉を避ける旨を毎回含める
- **ネガティブ要素の明示**: "no text, no watermark, no busy background"

#### 1-2. Few-shot 例示の挿入
プロンプト生成 LLM へのリクエストに、良質なプロンプト例を 1〜2 件含めると出力が安定する。

```
例：
A dark navy blue abstract background with soft glowing geometric shapes,
clean professional look, wide 16:9 format, left side has minimal clean space
for title overlay, subtle gradient from deep blue to midnight purple,
no text, no watermark, photorealistic lighting.
```

#### 1-3. ユーザー入力の構造化
自由記述をそのまま渡すより、カテゴリに分けて収集すると LLM が解釈しやすい：

| 入力項目 | 例 |
|---|---|
| テーマ・用途 | "テクノロジー系の企業紹介スライド" |
| 配色 | "ダークブルー × ゴールド" |
| 雰囲気 | "モダン・未来的・プロフェッショナル" |
| 避けたいもの | "人物なし・文字なし" |
| 構図の好み | "左上にタイトル用の余白が欲しい" |

---

### 2. 画像生成精度を上げる

#### 2-1. プロンプトの英語品質
- 日本語混じりや機械翻訳調の英語は避ける
- 形容詞を重ねすぎない（5〜8 個程度が限界）
- "cinematic", "award-winning", "ultra-detailed" などの過剰な修飾語は逆効果になる場合あり

#### 2-2. 解像度とアスペクト比
- スライド画像は `aspect_ratio="16:9"`, `image_size="2K"` が品質とコストのバランス点
- 確認用途なら `"1K"` でコスト削減も可

#### 2-3. Temperature / Thinking の活用
- `gemini-3-pro-image-preview` は Thinking 機能付き
- 複雑な構図指定の場合は `thinking_config` を有効化することで構図の解釈精度が上がる可能性あり（要検証）

#### 2-4. プロンプトの反復改善ループ
1. 生成された画像と元のプロンプトをペアで保存（ギャラリー機能で実装済み）
2. 気に入ったプロンプトのパターンを抽出
3. Few-shot 例示（1-2 参照）としてフィードバックする

---

## 参考リンク

- [Gemini API モデル一覧](https://ai.google.dev/gemini-api/docs/models)
- [画像生成ガイド](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini API 料金](https://ai.google.dev/gemini-api/docs/pricing)
- [google-genai Python SDK](https://github.com/googleapis/python-genai)
