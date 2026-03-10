# S16.2 -- Natural Language Chat Interface -- Checklist

## Data Contracts
- [x] Add `ChatRequest` model to `config/data_contracts.py`
- [x] Add `ChatResponse` model to `config/data_contracts.py`
- [x] Add `ChatHistoryResponse` model to `config/data_contracts.py`

## ChatEngine (`api/chat.py`)
- [x] Create `ChatEngine` class with constructor (conductor, memory, vault)
- [x] Implement intent detection (greeting, full_analysis, quick_question, visualize, visualize_context, compare, follow_up, general)
- [x] Implement ticker extraction from natural language (regex with .NS/.BO/.L support)
- [x] Implement company name resolution via Yahoo Finance + Polygon search
- [x] Implement expanded ticker/name stopwords to prevent false positives
- [x] Implement context grounding (build LLM prompt with verdict data)
- [x] Implement `process_message()` streaming method
- [x] Implement `process_message_sync()` non-streaming method
- [x] Implement Gemini streaming integration
- [x] Implement conversation history retrieval for context
- [x] Implement conversation persistence (store user + assistant messages)
- [x] Implement intent-specific system prompts
- [x] Implement "chart" SSE event for inline price chart rendering
- [x] Implement Indian market detection for context-aware queries

## API Endpoints
- [x] `POST /api/v1/chat` -- streaming SSE response
- [x] `POST /api/v1/chat` -- JSON fallback (Accept: application/json)
- [x] `GET /api/v1/chat/history/{session_id}` -- retrieve history
- [x] `DELETE /api/v1/chat/history/{session_id}` -- clear history
- [x] Register chat router in `app.py`

## App Integration
- [x] Initialize `ChatEngine` in `app.py` lifespan
- [x] Wire ChatEngine to app.state
- [x] Initialize VertexMemoryBank in lifespan

## Frontend
- [x] Add TypeScript types (ChatRequest, ChatEvent with chart type, ChatMessage, ChatHistoryResponse)
- [x] Add API client functions (streamChat, getChatHistory, deleteChatHistory)
- [x] Create chat page (`frontend/app/chat/page.tsx`)
- [x] Message bubble components (user + assistant with markdown rendering)
- [x] ChatMarkdown component with financial value colorization (green/red for +/-)
- [x] ChatPriceChart component with AreaChart (7D/1M/3M timeframes, currency-aware)
- [x] Inline price charts triggered by backend "chart" SSE event
- [x] Clickable example prompts in empty state
- [x] Streaming token display with "Analyzing..." indicator
- [x] Input area with send button and expanded placeholder
- [x] Auto-scroll behavior
- [x] Navigation link to /chat in layout

## Error Handling
- [x] Empty message -> 422
- [x] Message too long -> 422
- [x] Gemini failure -> graceful fallback
- [x] Memory bank unavailable -> continue without persistence

## Tests (`tests/test_chat.py`)
- [x] `test_chat_request_validation`
- [x] `test_chat_response_model`
- [x] `test_intent_detection_analyze`
- [x] `test_intent_detection_follow_up`
- [x] `test_intent_detection_compare`
- [x] `test_intent_detection_general`
- [x] `test_ticker_extraction`
- [x] `test_context_building`
- [x] `test_process_message_streaming`
- [x] `test_process_message_sync`
- [x] `test_chat_endpoint_streaming`
- [x] `test_chat_endpoint_json`
- [x] `test_chat_history_endpoint`
- [x] `test_chat_history_delete`
- [x] `test_conversation_persistence`
- [x] `test_context_grounding`
- [x] `test_gemini_failure_fallback`
- [x] `test_analysis_trigger`
- [x] `test_empty_message_rejected`
- [x] `test_message_too_long`

## Verification
- [x] All backend tests pass (51/51)
- [x] Ruff lint clean
- [x] Roadmap status updated to `done`
