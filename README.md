# Be Holmes | AI-Driven News Analysis Engine

![Version](https://img.shields.io/badge/Version-2.2.0-blue?style=flat-square)
![Build](https://img.shields.io/badge/Build-Stable-success?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)

> **Narrative vs. Reality.**

## Executive Summary

**Be Holmes** is an institutional-grade decision support system engineered to bridge the latency and information asymmetry between **off-chain global intelligence** and **on-chain prediction markets: Polymarket**.

In the domain of event derivatives, a critical "Expectation Gap" often exists between breaking news narratives and current probability pricing. Be Holmes functions as an end-to-end **Retrieval-Augmented Generation (RAG)** agent. It ingests unstructured intelligence, semantically maps it to live prediction contracts via neural search, and utilizes Large Language Models (LLMs) to compute an actionable **"Alpha Verdict"** based on implied probability and expected value (EV) logic.

<img width="3712" height="1802" alt="image" src="https://github.com/user-attachments/assets/99d38193-326d-4f27-aaa7-fe13edccca7a" />

---

## Core Architecture

The system operates on a strict, linear pipeline designed to minimize hallucination and maximize actionable financial insight.

### 1. Intelligence Injection (Input Layer)
The user inputs unstructured text data—ranging from breaking news headlines and social sentiment to geopolitical rumors. The system bypasses rigid keyword matching, utilizing an LLM to distill the input into **semantic intent** and **implied outcome**, ensuring high-fidelity search queries.

### 2. Neural Semantic Mapping (Retrieval Layer)
![Exa.ai](https://img.shields.io/badge/Neural_Search-Exa.ai-000000?style=flat-square&logo=googlechrome&logoColor=white)

* **Vector Embedding:** The engine converts input concepts into high-dimensional vector embeddings.
* **Neural Execution:** Performs a web-scale neural search targeting prediction market domains to identify correlated betting contracts.
* **Anti-Fragile Fallback:** Features a proprietary **Dual-Engine Mechanism**. If the primary Neural Search encounters latency, it seamlessly downgrades to a robust Keyword Search, ensuring **100% data availability**.
* **Fact-Checking:** Simultaneously verifies the authenticity of the input intelligence against authoritative global sources.

### 3. Bayesian Alpha Decoding (Analysis Layer)
![Google Gemini](https://img.shields.io/badge/Inference_Engine-Google_Gemini_2.5-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)

* **Data Stream:** Integrated with **Polymarket Gamma API** for real-time odds, liquidity depth, and volume, alongside **Binance API** for crypto-asset correlation.
* **Logic Synthesis:** The LLM acts as a Global Macro Portfolio Manager, synthesizing two distinct datasets:
    1.  **The Signal:** The material impact and credibility of the injected intelligence.
    2.  **The Price:** The current implied probability (odds) of the relevant contracts.
* **Output Protocol:** Generates an Investment Memorandum containing:
    * **EV Analysis:** Mathematical calculation of Expected Value (e.g., *Market implies 30%, Intel suggests 60% → Positive EV*).
    * **Execution Strategy:** Specific **Buy YES/NO** signals with target entry prices.

---

## Technical Stack

The architecture is built on a modular, high-performance stack designed for rapid inference and data throughput.

![Python](https://img.shields.io/badge/Core-Python_3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![API](https://img.shields.io/badge/Data_Stream-Polymarket_Gamma-000000?style=for-the-badge&logo=polymarket&logoColor=white)
![API](https://img.shields.io/badge/News_Feed-RSS_&_Binance-F7931A?style=for-the-badge&logo=rss&logoColor=white)
![LLM](https://img.shields.io/badge/Model-Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)

---

## Installation & Configuration

### Prerequisites
* Python 3.8+ environment
* API Credentials for **Exa.ai** (Neural Search) and **Google Gemini** (Reasoning).

### Quick Start

**1. Clone the repository**
```bash
git clone [https://github.com/your-username/be-holmes.git](https://github.com/your-username/be-holmes.git)
cd be-holmes
