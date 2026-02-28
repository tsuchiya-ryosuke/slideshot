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

# --- ベーシック認証 ---
AUTH_ID = os.getenv("AUTH_ID", "")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")

if not AUTH_ID or not AUTH_PASSWORD:
    st.error("サーバーの設定が不完全です。管理者に連絡してください。")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 ログイン")
    with st.form("login_form"):
        input_id = st.text_input("ID")
        input_pw = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")
        if submitted:
            if input_id == AUTH_ID and input_pw == AUTH_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("IDまたはパスワードが違います")
    st.stop()

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
    st.markdown("- プロンプト生成: `gemini-2.5-flash-lite`")
    st.markdown("- 画像生成: `gemini-3-pro-image-preview`")

# セッション初期化
if "gallery" not in st.session_state:
    st.session_state.gallery = []  # [{prompt, image, timestamp}, ...]
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""

st.markdown("---")

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

can_generate_prompt = bool(gemini_key and requirements)

if st.button("✨ プロンプト案を生成", disabled=not can_generate_prompt):
    with st.spinner("Gemini がプロンプトを考えています..."):
        try:
            genai.configure(api_key=gemini_key)
            text_model = genai.GenerativeModel("gemini-2.5-flash-lite")
            result = text_model.generate_content(
                f"""以下の要件を元に、画像生成AIへの英語プロンプトを1つ作成してください。

要件：
{requirements}

条件：
- スライド（16:9）に使用する画像です
- プロンプトは英語で書いてください
- 200〜350単語程度
- 具体的なビジュアル表現を含めてください（色、雰囲気、スタイル、構図など）
- プロンプトのみ出力し、説明文や前置きは不要です"""
            )
            generated = result.text.strip()
            st.session_state.generated_prompt = generated
            st.session_state.edited_prompt_area = generated
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

st.markdown("---")

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
                    st.session_state.edited_prompt_area = entry["prompt"]
                    st.rerun()

            st.caption("使用プロンプト:")
            st.code(entry["prompt"], language=None)

if st.session_state.gallery and st.button("🗑️ 履歴をクリア"):
    st.session_state.gallery = []
    st.rerun()

# --- フッター ---
st.markdown("---")
st.caption("プロンプト生成: Gemini 2.5 Flash Lite ／ 画像生成: Gemini 3 Pro Image (Nano Banana Pro, Google)")
