# 🌦️ Weather Agent — Multi-Tool Agentic Pipeline with PydanticAI + Groq

A Python project that builds a **real-world, multi-tool weather agent** using [PydanticAI](https://ai.pydantic.dev) and Groq's `llama-3.3-70b-versatile`. The agent autonomously chains three tools — geocoding, weather fetching, and local time lookup — to answer natural language weather questions with structured, validated responses.

It also features a **router agent** that classifies whether a query is weather-related before passing it to the main agent, demonstrating a basic multi-agent pattern.

---

## 📌 What It Does

You ask a weather question in plain English. The agent:

1. Calls `get_coordinates` to resolve the city name to latitude, longitude, and timezone
2. Calls `get_weather` and `get_local_time` in parallel using the resolved coordinates
3. Returns a fully validated `WeatherReport` object with city, temperature, condition, and a practical recommendation

If your query isn't weather-related, a lightweight **router agent** catches it first and short-circuits the pipeline — the main agent never runs.

All weather data is fetched live from the [Open-Meteo API](https://open-meteo.com/) — no API key required.

---

## 🔑 Key Concepts

### Multi-Tool Chaining
The agent is instructed to call tools in a specific order via the system prompt. PydanticAI handles the tool call loop automatically — the model reasons about which tool to call next until it has enough data to produce the final structured output:

```
get_coordinates → get_weather + get_local_time → WeatherReport
```

### Router Agent
A second lightweight agent runs before the main agent to classify the query:

```python
router = Agent(
    model='groq:llama-3.3-70b-versatile',
    output_type=bool,
    instructions="Determine if the user's message is asking about weather..."
)

is_weather = router.run_sync(user_string).output
if not is_weather:
    print("Sorry, I can only answer weather-related questions.")
    return
```

This keeps the main agent focused and prevents it from wasting tool calls on off-topic queries.

### Async Tools
Two of the three tools are `async` — they use `httpx.AsyncClient` to make non-blocking HTTP requests to external APIs. PydanticAI supports both sync and async tools on the same agent transparently:

```python
@agent.tool_plain
async def get_coordinates(city: str) -> dict:
    async with httpx.AsyncClient() as client:
        ...
```

### Structured Output
The final response is validated against a clean `WeatherReport` model:

```python
class WeatherReport(BaseModel):
    city: str
    temperature_c: float
    condition: str
    recommendation: str
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| [PydanticAI](https://ai.pydantic.dev) | Agent framework with native tool-calling and structured outputs |
| [Groq](https://groq.com/) | Fast LLM inference (LLaMA 3.3 70B) |
| [Pydantic v2](https://docs.pydantic.dev/) | Data validation and schema definition |
| [httpx](https://www.python-httpx.org/) | Async HTTP client for API requests |
| [Open-Meteo](https://open-meteo.com/) | Free, no-auth weather and geocoding APIs |
| [zoneinfo](https://docs.python.org/3/library/zoneinfo.html) | IANA timezone resolution (Python stdlib) |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Secure API key management |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Dark5301/weather-agent-pydanticai.git
cd weather-agent-pydanticai
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install pydantic-ai groq pydantic httpx python-dotenv
```

> `zoneinfo` is part of the Python standard library (Python 3.9+). No separate install needed.

### 4. Set up your environment variables

Create a `.env` file in the root of the project:

```env
GROQ_API_KEY=your_groq_api_key_here
```

> Get your free Groq API key at [console.groq.com](https://console.groq.com). The Open-Meteo API requires no key.

### 5. Run the script

```bash
python project2.py
```

---

## 📤 Example Session

```
Enter your query ("exit" for exit):
> What's the weather like in Delhi right now?

City: Delhi
Temperature (°C): 36.2
Weather Condition: Clear sky
Recommendation: Stay hydrated and avoid going out during peak afternoon hours.

Enter your query ("exit" for exit):
> What's the capital of France?

Sorry, I can only answer weather-related questions.

Enter your query ("exit" for exit):
> How about Mumbai?

City: Mumbai
Temperature (°C): 31.5
Weather Condition: Partly cloudy
Recommendation: Humid conditions expected — light clothing recommended.

Enter your query ("exit" for exit):
> exit
```

> Note: The second turn ("How about Mumbai?") works because conversation history is maintained — the agent understands "How about Mumbai?" as a follow-up weather question from prior context.

---

## ⚠️ Known Limitations

- **Ambiguous city names**: If you provide an ambiguous name (e.g. "Springfield"), the agent will ask for clarification before calling any tools, as instructed in the system prompt.
- **No session persistence**: Conversation history is held in memory only. Restarting the script clears all prior context.
- **Synchronous entry point**: The script uses `agent.run_sync()`. Internally, async tools are handled correctly by PydanticAI's event loop management — but for a production async application, use `await agent.run()` instead.
- **Router cost**: Every query, including off-topic ones, makes one additional LLM call to the router. For high-volume use, consider a lighter classification method.

---

## 🔮 Roadmap

- [ ] Add hourly and multi-day forecast support
- [ ] Surface `feels_like`, humidity, and wind speed in the output schema
- [ ] Persist conversation history between sessions
- [ ] Migrate to `agent.run()` for a fully async CLI
- [ ] Expand the router to support multiple specialised agents (e.g. weather, news, finance)

---

## 👤 Author

**Prince**
Aspiring AI/Cybersecurity Developer · Python · Bash · JavaScript
Building a portfolio at the intersection of AI agents and penetration testing.

---

## 📄 License

MIT License — feel free to fork, modify, and build on this.
