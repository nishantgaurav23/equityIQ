# S16.2 -- Natural Language Chat Interface

## Status: done
## Depends on: S16.1 (Vertex Memory Bank), S9.1 (Analyze Endpoint), S13.1 (Next.js Scaffold)

---

## 1. Goal

Add a conversational chat interface so users can ask natural-language questions about stocks and receive context-aware answers grounded in real analysis data. The system uses Gemini 3 Flash for response generation, streams responses to the frontend, and persists conversation history via the Vertex Memory Bank.

---

## 2. Deliverables

### Backend (`api/chat.py`)

| Item | Detail |
|------|--------|
| `POST /api/v1/chat` | Accept user message, return AI response (streaming SSE) |
| `GET /api/v1/chat/history/{session_id}` | Retrieve conversation history for a session |
| `DELETE /api/v1/chat/history/{session_id}` | Clear conversation history for a session |
| Chat engine class | `ChatEngine` in `api/chat.py` -- orchestrates context, LLM call, storage |

### Frontend (`frontend/app/chat/page.tsx`)

| Item | Detail |
|------|--------|
| Chat page | `/chat` route with message bubbles, input box, streaming display |
| Message components | User/assistant message bubbles with timestamps |
| Streaming support | Read SSE stream, render tokens incrementally |
| Context awareness | Show linked verdict cards when analysis is referenced |

### Integration

| Item | Detail |
|------|--------|
| Vertex Memory Bank | Store/retrieve conversation entries per session |
| Market Conductor | Trigger analysis when user asks about a new ticker |
| History linkage | Link chat messages to verdict session_ids |

---

## 3. API Specification

### POST /api/v1/chat

**Request body:**
```json
{
  "message": "Why did you rate AAPL as SELL?",
  "session_id": "optional-uuid-for-continuing-conversation",
  "user_id": "default",
  "ticker": "AAPL"
}
```

**Pydantic model:**
```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None  # auto-generated if absent
    user_id: str = "default"
    ticker: str | None = None  # optional context ticker
```

**Response:** Server-Sent Events (SSE) stream

```
data: {"type": "session", "session_id": "uuid-here"}

data: {"type": "token", "content": "Based on"}

data: {"type": "token", "content": " the analysis"}

data: {"type": "context", "ticker": "AAPL", "verdict_session_id": "abc-123"}

data: {"type": "chart", "tickers": ["AAPL"]}

data: {"type": "done", "full_response": "Based on the analysis..."}
```

**Non-streaming fallback:** If `Accept: application/json` header is present, return:
```json
{
  "session_id": "uuid",
  "response": "Based on the analysis...",
  "ticker": "AAPL",
  "verdict_session_id": "abc-123"
}
```

**Pydantic model:**
```python
class ChatResponse(BaseModel):
    session_id: str
    response: str
    ticker: str | None = None
    verdict_session_id: str | None = None
    timestamp: datetime
```

### GET /api/v1/chat/history/{session_id}

**Query params:** `limit: int = 50` (max 200)

**Response:**
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "entry_id": "uuid",
      "role": "user",
      "content": "Analyze AAPL for me",
      "ticker": "AAPL",
      "created_at": "2026-03-10T12:00:00Z"
    },
    {
      "entry_id": "uuid",
      "role": "assistant",
      "content": "Based on my analysis...",
      "ticker": "AAPL",
      "verdict_session_id": "abc-123",
      "created_at": "2026-03-10T12:00:01Z"
    }
  ]
}
```

### DELETE /api/v1/chat/history/{session_id}

**Response:** `{"deleted": true, "session_id": "uuid"}`

---

## 4. ChatEngine Design

```python
class ChatEngine:
    """Orchestrates chat: context retrieval, LLM generation, storage."""

    def __init__(
        self,
        conductor: MarketConductor,
        memory: VertexMemoryBank,
        vault: InsightVault,
    ):
        ...

    async def process_message(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[dict, None]:
        """
        1. Parse intent (analyze ticker, follow-up, comparison, general)
        2. Retrieve conversation history for session
        3. Gather grounding context (recent verdicts, agent details)
        4. Build prompt with system instructions + context + history
        5. Stream Gemini response tokens
        6. Store user message + assistant response in VertexMemoryBank
        7. Yield SSE events
        """

    async def process_message_sync(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """Non-streaming version for JSON responses."""
```

### Intent Detection

The ChatEngine detects user intent from the message (redesigned for smarter classification):

| Intent | Trigger Examples | Action |
|--------|-----------------|--------|
| `greeting` | "Hello", "Hi", "Good morning" | Warm conversational response |
| `full_analysis` | "Analyze AAPL", bare ticker "AAPL", "Evaluate GOOG" | Run full 7-agent analysis via conductor |
| `quick_question` | "What about TSLA?", "Tell me about MSFT" | Fetch lightweight data (price, company info) without full analysis |
| `visualize` | "Show me the AAPL chart", "Graph TSLA price" | Analysis + inline price chart |
| `visualize_context` | "Show chart" (after prior analysis) | Show chart for contextual ticker |
| `compare` | "Compare AAPL vs MSFT", "Which is better?" | Run/fetch analysis for both |
| `follow_up` | "Why did you say SELL?", "Explain the reasoning" | Use last verdict as context |
| `general` | "What is PE ratio?", "How does the stock market work?" | Answer from LLM knowledge |

Intent detection uses keyword matching + ticker extraction (regex for 1-12 uppercase letters with .NS/.BO/.L suffix support). Extensive stopword lists prevent false positives (common English words, exchange names, financial terms). Company name resolution via Yahoo Finance + Polygon search enables natural queries like "Tell me about Tata Motors".

### Context Grounding

When responding about a specific ticker, the ChatEngine includes in the LLM prompt:
- The most recent `FinalVerdict` for that ticker (signal, confidence, key_drivers)
- `analyst_details` from each agent (reasoning, key_metrics)
- `risk_summary` and `price_target`
- Previous messages in the conversation (up to 20 turns)

This ensures the LLM gives answers grounded in actual analysis data, not hallucinated financial advice.

### System Prompt

The system prompt has been redesigned to support true conversational financial AI:
- Answers ANY question contextually (price, market cap, fundamentals, macro, general finance)
- Uses conversation history to avoid repeating itself
- Fetches lightweight data (price, company info) without running full 7-agent analysis
- Only triggers full multi-agent analysis when user explicitly asks for deep analysis
- Reuses prior analysis from conversation history for follow-up questions
- Intent-specific prompt sections are injected based on detected intent

---

## 5. Frontend Specification

### Chat Page (`frontend/app/chat/page.tsx`)

**Layout:**
- Full-height page with glass panel
- Message area (scrollable, auto-scroll to bottom)
- Input area at bottom (text input + send button)
- Optional: sidebar showing active ticker context

**Message Bubble Components:**
- User messages: right-aligned, accent color background
- Assistant messages: left-aligned, glass-dark background
- Streaming indicator: pulsing dots while generating
- Verdict card: inline mini-card when analysis is referenced

**Streaming Display:**
- Use `EventSource` or `fetch` with `ReadableStream` to consume SSE
- Render tokens as they arrive (append to message content)
- Show typing indicator until first token arrives
- Smooth scroll to bottom as new content appears

### API Client Extensions (`frontend/lib/api.ts`)

```typescript
// New functions
async function* streamChat(request: ChatRequest): AsyncGenerator<ChatEvent>
async function getChatHistory(sessionId: string, limit?: number): Promise<ChatHistoryResponse>
async function deleteChatHistory(sessionId: string): Promise<void>
```

### TypeScript Types (`frontend/types/api.ts`)

```typescript
interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  ticker?: string;
}

interface ChatEvent {
  type: "session" | "token" | "context" | "chart" | "done";
  session_id?: string;
  content?: string;
  ticker?: string;
  tickers?: string[];  // list of tickers to render charts for
  verdict_session_id?: string;
  full_response?: string;
}

interface ChatMessage {
  entry_id: string;
  role: "user" | "assistant";
  content: string;
  ticker?: string;
  verdict_session_id?: string;
  created_at: string;
}

interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
}
```

---

## 6. Gemini Integration

### LLM Client

Use `google-genai` Python SDK (already in project dependencies via ADK):

```python
from google import genai

client = genai.Client()

async def generate_streaming(prompt: str, history: list[dict]) -> AsyncGenerator[str, None]:
    response = await client.aio.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=_build_contents(prompt, history),
    )
    async for chunk in response:
        if chunk.text:
            yield chunk.text
```

### Conversation History Format

Map ConversationEntry records to Gemini's content format:
```python
[
    {"role": "user", "parts": [{"text": "Analyze AAPL"}]},
    {"role": "model", "parts": [{"text": "Based on the analysis..."}]},
]
```

---

## 7. Error Handling

| Scenario | Response |
|----------|----------|
| Empty message | 422 Unprocessable Entity |
| Message too long (>2000 chars) | 422 Unprocessable Entity |
| Invalid session_id format | 422 Unprocessable Entity |
| Gemini API failure | SSE error event + fallback message |
| Analysis timeout | Respond with available cached data |
| No conversation found | 404 Not Found (for GET history) |
| Memory bank unavailable | Continue without persistence, warn in logs |

---

## 8. Testing Requirements

### Unit Tests (`tests/test_chat.py`)

| Test | Description |
|------|------------|
| `test_chat_request_validation` | Valid/invalid ChatRequest models |
| `test_chat_response_model` | ChatResponse serialization |
| `test_intent_detection_analyze` | "Analyze AAPL" -> analyze intent |
| `test_intent_detection_follow_up` | "Why SELL?" -> follow_up intent |
| `test_intent_detection_compare` | "Compare AAPL vs MSFT" -> compare intent |
| `test_intent_detection_general` | "What is PE ratio?" -> general intent |
| `test_ticker_extraction` | Extract ticker symbols from messages |
| `test_context_building` | Build LLM prompt with verdict context |
| `test_process_message_streaming` | Full streaming flow (mocked Gemini) |
| `test_process_message_sync` | Non-streaming JSON response |
| `test_chat_endpoint_streaming` | POST /api/v1/chat SSE response |
| `test_chat_endpoint_json` | POST /api/v1/chat JSON response |
| `test_chat_history_endpoint` | GET /api/v1/chat/history/{session_id} |
| `test_chat_history_delete` | DELETE /api/v1/chat/history/{session_id} |
| `test_conversation_persistence` | Messages stored in VertexMemoryBank |
| `test_context_grounding` | LLM prompt includes verdict data |
| `test_gemini_failure_fallback` | Graceful error on LLM failure |
| `test_analysis_trigger` | "Analyze TSLA" triggers conductor |
| `test_empty_message_rejected` | Empty string returns 422 |
| `test_message_too_long` | >2000 chars returns 422 |

### Frontend Tests (`frontend/__tests__/chat.test.tsx`)

| Test | Description |
|------|------------|
| `test_chat_page_renders` | Page mounts with input and send button |
| `test_send_message` | User types message and clicks send |
| `test_message_display` | User and assistant messages render correctly |
| `test_streaming_display` | Tokens appear incrementally |
| `test_auto_scroll` | Chat scrolls to bottom on new message |
| `test_session_persistence` | Session ID maintained across messages |

---

## 9. File Map

| File | Purpose |
|------|---------|
| `api/chat.py` | ChatEngine class, chat router, intent detection, company name resolution, context building |
| `config/data_contracts.py` | ChatRequest, ChatResponse models (add to existing) |
| `api/routes.py` | Include chat router |
| `app.py` | Initialize ChatEngine in lifespan |
| `frontend/app/chat/page.tsx` | Chat page UI with inline charts and markdown rendering |
| `frontend/components/ChatMarkdown.tsx` | Markdown renderer with financial value colorization (green/red for +/-) |
| `frontend/components/ChatPriceChart.tsx` | Inline price chart component (AreaChart via Recharts, 7D/1M/3M timeframes) |
| `frontend/lib/api.ts` | streamChat, getChatHistory, deleteChatHistory |
| `frontend/types/api.ts` | ChatRequest, ChatEvent (with chart type), ChatMessage types |
| `tests/test_chat.py` | Backend tests |

---

## 10. Acceptance Criteria

1. `POST /api/v1/chat` accepts a message and streams back SSE tokens
2. Non-streaming fallback returns JSON when `Accept: application/json`
3. Intent detection correctly classifies analyze, follow_up, compare, general
4. Ticker extraction parses symbols from natural language
5. Context grounding includes relevant FinalVerdict data in LLM prompt
6. Conversation history persisted in VertexMemoryBank
7. `GET /api/v1/chat/history/{session_id}` returns conversation entries
8. `DELETE /api/v1/chat/history/{session_id}` clears history
9. "Analyze AAPL" triggers MarketConductor.analyze()
10. Frontend chat page renders with message bubbles and streaming display
11. All backend tests pass with mocked Gemini
12. Graceful fallback when Gemini API fails
