# Vapi Provider Reference

## LLM / Model Providers

| Provider | `provider` value | Notable models |
|---|---|---|
| OpenAI | `"openai"` | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| Anthropic | `"anthropic"` | `claude-opus-4-20250514`, `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001` |
| Google | `"google"` | `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash` |
| Groq | `"groq"` | `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768` |
| Together AI | `"together-ai"` | Various open source models |
| Perplexity | `"perplexity"` | `llama-3.1-sonar-large-128k-online` |
| DeepSeek | `"deep-seek"` | `deepseek-chat` |
| xAI | `"xai"` | `grok-beta` |
| Anyscale | `"anyscale"` | Various |
| Openrouter | `"openrouter"` | Any model via OpenRouter |
| Custom OpenAI-compatible | `"custom-llm"` | Bring your own endpoint |

## Voice / TTS Providers

| Provider | `provider` value | Notes |
|---|---|---|
| ElevenLabs | `"11labs"` | Highest quality; voice cloning available |
| OpenAI TTS | `"openai"` | `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` |
| Azure Cognitive | `"azure"` | Wide language support; enterprise grade |
| PlayHT | `"playht"` | High quality, fast |
| Deepgram Aura | `"deepgram"` | Low latency, good for real-time |
| Cartesia | `"cartesia"` | Ultra-low latency |
| Rime | `"rime-ai"` | Natural expressive voices |
| Smallest AI | `"smallest-ai"` | Fast, cost-efficient |
| Neets | `"neets"` | Multiple voice styles |
| Lmnt | `"lmnt"` | Natural, customizable |
| Murf | `"murf"` | Studio-quality voices |
| Custom TTS | `"custom-voice"` | Bring your own TTS server |

## Transcriber / STT Providers

| Provider | `provider` value | Notes |
|---|---|---|
| Deepgram | `"deepgram"` | Best latency; recommended for real-time |
| AssemblyAI | `"assembly-ai"` | High accuracy; streaming |
| OpenAI Whisper | `"openai"` | High accuracy; slightly higher latency |
| Gladia | `"gladia"` | Multilingual focus |
| Talkscriber | `"talkscriber"` | Specialized telephony |
| Custom | `"custom-transcriber"` | Bring your own STT server |

## Deepgram model options
- `nova-3` — latest, best accuracy (recommended)
- `nova-2` — good balance
- `nova-2-phonecall` — optimized for telephone audio
- `nova-2-meeting` — optimized for meeting audio
- `enhanced` — older but reliable
- `base` — fastest, lower accuracy

## ElevenLabs notable voice IDs
- `21m00Tcm4TlvDq8ikWAM` — Rachel (warm female)
- `AZnzlk1XvdvUeBnXmlld` — Domi (strong female)
- `EXAVITQu4vr4xnSDxMaL` — Bella (soft female)
- `ErXwobaYiN019PkySvjV` — Antoni (well-rounded male)
- `MF3mGyEYCl7XYWbV9V6O` — Elli (emotional female)
- `TxGEqnHWrfWFTfGW9XjX` — Josh (deep male)
- `VR6AewLTigWG4xSOukaG` — Arnold (crisp male)
- `pNInz6obpgDQGcFmaJgB` — Adam (deep male)
- `yoZ06aMxZJJ28mfd3POQ` — Sam (raspy male)

## Telephony providers (for phone numbers)
- Twilio
- Vonage
- Telnyx
- Vapi free numbers (limited, for testing)