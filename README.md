# Japanese Sake Guide App | 日本酒ガイドアプリ

An AI-powered web application to help users discover and learn about Japanese sake (nihonshu). Built with Streamlit, LangGraph, and OpenAI.

日本酒（にほんしゅ）の発見と学習をサポートするAI搭載ウェブアプリケーション。Streamlit、LangGraph、OpenAIで構築。

## Features | 機能

- **Sake Recommendations** | おすすめ検索: Get personalized sake recommendations based on your preferences
- **Sake Information** | 銘柄情報: Learn about specific sake brands, breweries, and production methods
- **Rankings** | ランキング: Access top-rated sake from trusted sources (Sakenowa, Saketime)
- **Instagram Search** | Instagram検索: Find social media content and reviews about sake
- **Bilingual Support** | 日英対応: Full support for both Japanese and English

## Tech Stack | 技術スタック

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Agent Framework**: [LangGraph](https://langchain-ai.github.io/langgraph/)
- **LLM**: [OpenAI GPT-4o](https://openai.com/)
- **Web Search**: [Tavily API](https://tavily.com/)
- **Deployment**: [Streamlit Cloud](https://streamlit.io/cloud)

## Data Sources | データソース

The app retrieves sake information from:
- [Sakenowa](https://sakenowa.com/en/ranking) - Japanese sake database with rankings
- [Saketime](https://www.saketime.jp/ranking/) - Japanese sake ranking site
- Instagram (via web search)

## Quick Start | クイックスタート

### Prerequisites | 必要条件

- Python 3.9+
- OpenAI API key
- Tavily API key

### Local Development | ローカル開発

1. **Clone the repository | リポジトリをクローン**
   ```bash
   git clone https://github.com/yourusername/japan_sake_guide_app.git
   cd japan_sake_guide_app
   ```

2. **Create virtual environment | 仮想環境を作成**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies | 依存関係をインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets | シークレットを設定**
   ```bash
   cp secrets.toml.example .streamlit/secrets.toml
   ```
   Edit `.streamlit/secrets.toml` and add your API keys:
   ```toml
   OPENAI_API_KEY = "your-openai-api-key"
   TAVILY_API_KEY = "your-tavily-api-key"
   INSTAGRAM_ACCESS_TOKEN = "optional-instagram-token"
   ```

5. **Run the app | アプリを起動**
   ```bash
   streamlit run app.py
   ```

6. Open your browser at `http://localhost:8501`

## Deploy to Streamlit Cloud | Streamlit Cloudへのデプロイ

1. **Fork/Push to GitHub**
   - Push this repository to your GitHub account

2. **Connect to Streamlit Cloud**
   - Go to [Streamlit Cloud](https://streamlit.io/cloud)
   - Click "New app"
   - Select your repository and `app.py` as the main file

3. **Configure Secrets**
   - In Streamlit Cloud settings, go to "Secrets"
   - Add your API keys:
   ```toml
   OPENAI_API_KEY = "your-openai-api-key"
   TAVILY_API_KEY = "your-tavily-api-key"
   INSTAGRAM_ACCESS_TOKEN = "optional-instagram-token"
   ```

4. **Deploy**
   - Click "Deploy" and wait for the app to build

## Project Structure | プロジェクト構造

```
japan_sake_guide_app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── secrets.toml.example   # Example secrets configuration
├── README.md             # This file
├── .streamlit/
│   └── config.toml       # Streamlit theme configuration
├── agents/
│   ├── __init__.py
│   ├── sake_agent.py     # LangGraph agent workflow
│   └── tools.py          # Search tools (Tavily, Instagram)
├── config/
│   ├── __init__.py
│   └── settings.py       # Application settings
└── utils/
    ├── __init__.py
    └── helpers.py        # Utility functions
```

## Usage Examples | 使用例

### English
- "What are the top-rated sake this year?"
- "Tell me about Dassai 23"
- "Recommend a fruity sake for beginners"
- "What sake pairs well with sushi?"
- "Find Instagram posts about Kubota sake"

### 日本語
- "今年人気の日本酒は何ですか？"
- "獺祭23について教えてください"
- "初心者におすすめのフルーティな日本酒は？"
- "寿司に合う日本酒を教えてください"
- "久保田のInstagram投稿を探して"

## API Keys | APIキー

### OpenAI API
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an account or sign in
3. Generate a new API key

### Tavily API
1. Go to [Tavily](https://tavily.com/)
2. Sign up for an account
3. Get your API key from the dashboard

### Instagram API (Optional)
For enhanced Instagram search:
1. Create a [Facebook Developer](https://developers.facebook.com/) account
2. Set up Instagram Basic Display API
3. Generate an access token

## Contributing | 貢献

Contributions are welcome! Please feel free to submit a Pull Request.

## License | ライセンス

MIT License

## Acknowledgments | 謝辞

- Sake data from [Sakenowa](https://sakenowa.com/) and [Saketime](https://www.saketime.jp/)
- Built with [Streamlit](https://streamlit.io/), [LangGraph](https://langchain-ai.github.io/langgraph/), and [OpenAI](https://openai.com/)
