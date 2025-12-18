# AWS Bedrock Model Recommendations for Architecture Diagram Generator

## 🏆 TOP RECOMMENDATIONS

### Best High-End Model (Recommended)
**Model:** `anthropic.claude-3-5-haiku-20241022-v1:0`  
**Region:** us-east-1, us-west-2, ap-southeast-1, eu-west-1  
**Why:** Latest high-end model, excellent quality, works with on-demand throughput  
**Status:** ✅ Works without inference profile

### Alternative High-End Model (Stable)
**Model:** `anthropic.claude-3-5-sonnet-20241022-v2:0`  
**Region:** All major regions  
**Why:** Proven stable, high quality, widely available  
**Status:** ✅ Works without inference profile

### Fastest Model (Speed Priority)
**Model:** `anthropic.claude-3-5-haiku-20241022-v1:0`  
**Region:** Most regions  
**Why:** Fastest responses, good quality, cost-effective  
**Status:** ✅ Works without inference profile

---

## 📊 BEST MODELS BY REGION

### US-EAST-1 (25 models available)
- **Best Sonnet:** `anthropic.claude-3-5-haiku-20241022-v1:0` (if available) or `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Best Haiku:** `anthropic.claude-3-5-haiku-20241022-v1:0`
- **Alternative:** `anthropic.claude-sonnet-4-20250514-v1:0`

### US-WEST-2 (31 models available - MOST OPTIONS)
- **Best Sonnet:** `anthropic.claude-3-5-haiku-20241022-v1:0` (if available) or `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Best Haiku:** `anthropic.claude-3-5-haiku-20241022-v1:0`
- **Alternative:** `anthropic.claude-sonnet-4-20250514-v1:0`

### EU-WEST-1 (11 models available)
- **Best Sonnet:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Best Haiku:** `anthropic.claude-3-5-haiku-20241022-v1:0`

### AP-SOUTHEAST-1 (11 models available)
- **Best Sonnet:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Best Haiku:** `anthropic.claude-3-5-haiku-20241022-v1:0`

### EU-CENTRAL-1 (10 models available)
- **Best Sonnet:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Best Haiku:** `anthropic.claude-3-5-haiku-20241022-v1:0`

---

## ⚠️ IMPORTANT NOTES

### Models Requiring Inference Profiles (NOT Recommended for Direct Use)
These models require inference profiles and cannot be used directly:
- `anthropic.claude-sonnet-4-5-20250929-v1:0` ❌
- `anthropic.claude-haiku-4-5-20251001-v1:0` ❌
- `anthropic.claude-opus-4-5-20251101-v1:0` ❌

### Models That Work with On-Demand (Recommended)
These models work directly without inference profiles:
- `anthropic.claude-3-5-haiku-20241022-v1:0` ✅
- `anthropic.claude-3-5-sonnet-20241022-v2:0` ✅
- `anthropic.claude-3-5-haiku-20241022-v1:0` ✅
- `anthropic.claude-sonnet-4-20250514-v1:0` ✅
- `anthropic.claude-3-sonnet-20240229-v1:0` ✅

---

## 🎯 RECOMMENDATION FOR YOUR USE CASE

**For Architecture Diagram Generation:**

1. **Primary Choice:** `anthropic.claude-3-5-haiku-20241022-v1:0`
   - Region: `us-east-1` or `us-west-2`
   - Best quality and latest features
   - Works with on-demand throughput

2. **Fallback Choice:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - Region: `us-east-1` (or any region)
   - Stable and reliable
   - Currently configured in your app

3. **Speed Priority:** `anthropic.claude-3-5-haiku-20241022-v1:0`
   - Region: `us-east-1` (or any region)
   - Fastest responses
   - Good quality for most use cases

---

## 📝 HOW TO UPDATE

To change the model, update these files:
1. `Frontend/src/App.tsx` - Default model ID
2. `Backend/main.py` - Default model ID in API endpoint
3. `pdf_extractor.py` - Default model ID in summarize function

Or simply change the model ID in the frontend UI when uploading a PDF.

---

## 🔍 ALL AVAILABLE REGIONS WITH CLAUDE MODELS

- ap-northeast-1, ap-northeast-2, ap-northeast-3
- ap-south-1, ap-south-2
- ap-southeast-1, ap-southeast-2
- ca-central-1
- eu-central-1, eu-north-1
- eu-west-1, eu-west-2, eu-west-3
- me-central-1
- sa-east-1
- us-east-1, us-east-2
- us-west-1, us-west-2

**Most models available:** US-WEST-2 (31 models)  
**Most stable:** US-EAST-1 (25 models)

