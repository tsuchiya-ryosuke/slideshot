import os
import base64
from io import BytesIO

import streamlit as st
import google.generativeai as genai
from google.generativeai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# --- ページ設定 ---
st.set_page_config(
    page_title="SlideShot - スライド用画像生成",
    page_icon="🖼️",
    layout="wide",
)

st.title("🖼️ SlideShot")
st.caption("スライド用の画像を、要件からワンストップで生成します。")

# --- サイドバー: APIキー設定 ---
with st.sidebar:
    st.header("⚙️ 設定")
    env_key = os.getenv("GEMINI_API_KEY", "")
    if env_key:
        st.success("GEMINI_API_KEY を環境変数から読み込みました")
        gemini_key = env_key
    else:
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza...",
        )
        st.caption(
            "APIキーはセッション中のみ保持されます。"
            "`.env` に `GEMINI_API_KEY` を設定すると自動で読み込まれます。"
        )

    st.markdown("---")
    st.markdown("**使用モデル**")
    st.markdown("- プロンプト生成: `gemini-2.0-flash`")
    st.markdown("- 画像生成: `gemini-3-pro-image-preview`")

# --- スタイルプリセット定義 ---
MOOD_PRESETS = {
    "ミニマル": "minimalist, clean, lots of whitespace, simple shapes",
    "コーポレート": "corporate, professional, business-oriented, polished",
    "クリエイティブ": "creative, artistic, expressive, unique design",
    "テック": "technology, futuristic, digital, data-driven, modern",
    "アカデミック": "academic, scholarly, structured, informative",
}

COLOR_PRESETS = {
    "ライト": "light background, white tones, airy, bright",
    "ダーク": "dark background, deep colors, dramatic lighting",
    "カラフル": "vibrant colors, colorful, bold palette",
    "モノクロ": "monochrome, black and white, grayscale",
}

LAYOUT_PRESETS = {
    "フラット": "flat design, 2D, geometric shapes",
    "グラジエント": "gradient colors, smooth transitions, flowing",
    "写真風": "photorealistic, cinematic, photo-like quality",
    "イラスト風": "illustration style, vector art, hand-drawn feel",
}

# セッション初期化
if "gallery" not in st.session_state:
    st.session_state.gallery = []  # [{prompt, image, timestamp}, ...]
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""

# --- Step 1: 要件 & スタイル入力 ---
st.markdown("---")
st.subheader("Step 1｜要件とスタイルを入力する")

col_req, col_style = st.columns([3, 2])

with col_req:
    requirements = st.text_area(
        "欲しい画像の要件（箇条書きでOK）",
        height=180,
        placeholder="""例：
- テクノロジー系スライドに使いたい
- 抽象的なネットワーク・接続のイメージ
- ダークブルー系の配色
- 人物は不要
- シンプルでクリーン、余白が多めがよい""",
    )

with col_style:
    st.markdown("**スタイルプリセット（任意・複数選択可）**")

    st.markdown("*雰囲気*")
    selected_mood = st.radio(
        "雰囲気",
        options=["指定なし"] + list(MOOD_PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("*配色*")
    selected_color = st.radio(
        "配色",
        options=["指定なし"] + list(COLOR_PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("*レイアウト*")
    selected_layout = st.radio(
        "レイアウト",
        options=["指定なし"] + list(LAYOUT_PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

# 選択済みスタイルのサマリ表示
selected_styles = []
if selected_mood != "指定なし":
    selected_styles.append(f"**{selected_mood}**")
if selected_color != "指定なし":
    selected_styles.append(f"**{selected_color}**")
if selected_layout != "指定なし":
    selected_styles.append(f"**{selected_layout}**")
if selected_styles:
    st.info(f"選択中のスタイル: {' / '.join(selected_styles)}")

# --- Step 2: プロンプト生成 ---
st.markdown("---")
st.subheader("Step 2｜画像生成プロンプトを生成する")

style_hint_parts = []
if selected_mood != "指定なし":
    style_hint_parts.append(f"雰囲気: {selected_mood}（{MOOD_PRESETS[selected_mood]}）")
if selected_color != "指定なし":
    style_hint_parts.append(f"配色: {selected_color}（{COLOR_PRESETS[selected_color]}）")
if selected_layout != "指定なし":
    style_hint_parts.append(f"レイアウト: {selected_layout}（{LAYOUT_PRESETS[selected_layout]}）")
style_hint = "\n".join(style_hint_parts) if style_hint_parts else "（スタイル指定なし）"

can_generate_prompt = bool(gemini_key and requirements)

if st.button("✨ プロンプト案を生成", disabled=not can_generate_prompt):
    with st.spinner("Gemini がプロンプトを考えています..."):
        try:
            genai.configure(api_key=gemini_key)
            text_model = genai.GenerativeModel("gemini-2.0-flash")
            style_section = f"\nスタイル指定:\n{style_hint}" if style_hint_parts else ""
            result = text_model.generate_content(
                f"""以下の要件を元に、画像生成AIへの英語プロンプトを1つ作成してください。

要件：
{requirements}{style_section}

条件：
- スライド（16:9）に使用する画像です
- プロンプトは英語で書いてください
- 200〜350単語程度
- 具体的なビジュアル表現を含めてください（色、雰囲気、スタイル、構図など）
- プロンプトのみ出力し、説明文や前置きは不要です"""
            )
            st.session_state.generated_prompt = result.text.strip()
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info("よくある原因: APIキーが無効、またはGemini APIの利用制限に達した可能性があります。")

edited_prompt = st.text_area(
    "生成されたプロンプト（自由に編集できます）",
    value=st.session_state.generated_prompt,
    height=220,
    placeholder="先にプロンプト案を生成するか、ここに直接英語プロンプトを入力してください。",
    key="edited_prompt_area",
)

if edited_prompt:
    if st.button("📋 プロンプトをコピー"):
        st.code(edited_prompt, language=None)
        st.caption("上のテキストをコピーしてください。")

# --- Step 3: 画像生成 ---
st.markdown("---")
st.subheader("Step 3｜画像を生成する")

can_generate_image = bool(gemini_key and edited_prompt)

if st.button("🎨 画像を生成", type="primary", disabled=not can_generate_image):
    with st.spinner("Nano Banana Pro が画像を生成しています（16:9）..."):
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-3-pro-image-preview")

            full_prompt = (
                edited_prompt.strip()
                + " The image must be in 16:9 landscape aspect ratio, "
                "suitable for a presentation slide. "
                "High quality, professional, clean composition."
            )

            response = model.generate_content(
                full_prompt,
                generation_config=types.GenerationConfig(
                    response_modalities=["image", "text"],
                ),
            )

            image_data = None
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image_data = part.inline_data.data
                    break

            if image_data:
                image = Image.open(BytesIO(base64.b64decode(image_data)))
                st.session_state.gallery.insert(0, {
                    "prompt": edited_prompt.strip(),
                    "image": image,
                })
            else:
                st.error("画像データが取得できませんでした。プロンプトを変更して再試行してください。")
                st.info(
                    "よくある原因:\n"
                    "- プロンプトにポリシー違反のコンテンツが含まれている\n"
                    "- モデルの応答形式が変わった（インラインデータが返らなかった）\n"
                    "- APIキーの権限不足"
                )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info(
                "よくある原因:\n"
                "- APIキーが無効か期限切れ\n"
                "- `gemini-3-pro-image-preview` モデルへのアクセス権がない\n"
                "- ネットワーク接続の問題"
            )

# --- 最新の生成画像を表示 ---
if st.session_state.gallery:
    latest = st.session_state.gallery[0]
    st.image(latest["image"], use_container_width=True, caption="最新の生成画像（16:9）")

    buf = BytesIO()
    latest["image"].save(buf, format="PNG")
    st.download_button(
        label="📥 画像をダウンロード (PNG)",
        data=buf.getvalue(),
        file_name="slide_image.png",
        mime="image/png",
    )

# --- ギャラリー（セッション履歴） ---
if len(st.session_state.gallery) > 1:
    st.markdown("---")
    st.subheader(f"📚 生成履歴（{len(st.session_state.gallery)} 件）")

    for i, entry in enumerate(st.session_state.gallery[1:], start=1):
        with st.expander(f"#{i + 1}  （クリックして展開）"):
            st.image(entry["image"], use_container_width=True)

            buf = BytesIO()
            entry["image"].save(buf, format="PNG")
            col_dl, col_reuse = st.columns(2)
            with col_dl:
                st.download_button(
                    label="📥 ダウンロード",
                    data=buf.getvalue(),
                    file_name=f"slide_image_{i + 1}.png",
                    mime="image/png",
                    key=f"dl_{i}",
                )
            with col_reuse:
                if st.button("🔄 このプロンプトを再利用", key=f"reuse_{i}"):
                    st.session_state.generated_prompt = entry["prompt"]
                    st.rerun()

            st.caption("使用プロンプト:")
            st.code(entry["prompt"], language=None)

if st.session_state.gallery and st.button("🗑️ 履歴をクリア"):
    st.session_state.gallery = []
    st.rerun()

# --- フッター ---
st.markdown("---")
st.caption("プロンプト生成: Gemini 2.0 Flash ／ 画像生成: Gemini 3 Pro Image (Nano Banana Pro, Google)")
