# ✨ FLOWORK : Visual AI Workflow Automation Platform (AGENT OS)

<p align="center">
  <img src="https://flowork.cloud/images/flowork_2.webp" alt="Flowork Synapse Logo">
</p>

> **PROTOCOL GENESIS: WRITTEN FROM ZERO**
>
> Twelve months ago, my physical existence halted. A shattered spine left me paralyzed, isolated in a room while the outside world stripped away everything I had built—my assets, my home, my family.
>
> I had zero control. Zero mobility. Zero trust in centralized systems that had failed me.
>
> From that absolute zero, Flowork was born. It was not built as a startup; it was built as a survival mechanism. I needed a system that could operate autonomously when I could not. A system where the "brain" (Core) lived with me, not on some rented server that could be turned off by a stranger.
>
> This is not just another automation tool. It is a battle plan for reclaiming digital sovereignty. We are building an **Agent OS** that runs on anything—from old laptops to future robots—because when you have lost everything, you realize that the only reliable infrastructure is the one you control entirely.
>
> Welcome to the resistance.

---

<p align="center">
  <a href="https://github.com/flowork-dev/Visual-AI-Workflow-Automation-Platform">
  <img src="https://img.shields.io/github/stars/flowork-dev/Visual-AI-Workflow-Automation-Platform?style=social" alt="GitHub stars"></a>
  <a href="https://docs.flowork.cloud/">
  <img src="https://img.shields.io/badge/Docs-Read%20Now-blue?logo=gitbook" alt="Documentation"></a>
  <a href="https://t.me/FLOWORK_AUTOMATION">
  <img src="https://img.shields.io/badge/Telegram-Join%20Chat-blue?logo=telegram" alt="Telegram"></a>
  <a href="https://discord.gg/Gv7h5fWZY">
  <img src="https://img.shields.io/discord/1234567890?color=5865F2&logo=discord&logoColor=white" alt="Discord"></a>
</p>

Flowork is a **sovereign, self-hosted Agent Operating System** designed for *Global Distributed Scalability and Absolute User Data Control*.

Unlike traditional cloud platforms that rent you your own data, Flowork's **Split-Brain Architecture** separates the interface (GUI on global CDN) from the core logic (Gateway & Kernel on YOUR hardware). This ensures that while you get the speed of the cloud, your sensitive data and AI models never leave your physical premise.

## 🌟 Table of Contents

* [✨ Core Philosophy: Privacy & Data Sovereignty](#1-core-philosophy-privacy-data-sovereignty)
* [🚀 Architectural Advantages (Split-Brain)](#2-architectural-advantages-performance)
* [🌐 Multi-Language Agent Runner](#3-multi-language-runner-engine)
* [🧠 AI Powerhouse & Developer Tools](#5-ai-powerhouse-developer-tools)
* [🔗 Collaboration & Resource Sharing](#6-collaboration-resource-sharing)
* [🛠️ Debugging and Diagnostics](#7-debugging-and-diagnostics-features)
* [⚙️ Quick Installation (Docker)](#8-quick-installation-setup-guide-docker)
* [🗺️ Roadmap (Agent OS Vision)](#roadmap-agent-os-vision)
* [🌐 Community](#9-resources-community)

-----

## 1\. ✨ Core Philosophy: Privacy & Data Sovereignty

We ensure user privacy with the principle: **"The GUI is a Window, Your Server is the Vault."**

  * **User Data Sovereignty (Primary Privacy):** **All databases** (SQLite/PostgreSQL) and private user data **reside exclusively on your server** (self-hosted). Flowork never stores your sensitive data on third-party servers.
  * **Crypto-Secured Access (Zero-Trust):** We utilize **Web3 Crypto Technology (Private Key)** for admin authentication. No passwords to leak. Access is cryptographically verified.
  * **Enterprise Ready Audit Trail:** All administrative activities are logged locally, essential for compliance and security.

## 2\. 🚀 Architectural Advantages (Split-Brain)

Flowork's architecture is designed from the ground up to handle massive, distributed execution loads with minimal infrastructure cost.

  * **Decoupled Execution Model:** Our Core Kernel runs in a separate process from the Gateway, ensuring stability.
  * **AI Provider Agnostic:** Not locked into a single vendor. Use cloud AI (Gemini, ChatGPT) or **Local AI** (*on-premise* models like Llama/SDXL) running on your own GPU/CPU.
  * **Resource Efficiency:** Uses **sharded SQLite** by default for **zero-setup** high performance, capable of handling millions of jobs without complex database clusters.

-----

### 🛡️ Enterprise-Grade Resilience (Hardened)

Flowork is built for mission-critical workloads where failure is not an option.

  * **True Horizontal Scalability:** Gateway is stateless. Scale it infinitely behind a load balancer.
  * **Intelligent Backpressure:** Automatically defers loads (HTTP 429) when queues are full to prevent crashes.
  * **Fairness & Abuse Protection:** Integrated Token Bucket rate limiting per user/engine.
  * **Resilience Patterns:** Circuit Breakers and Job Watchdogs prevent cascading failures and zombie jobs.

-----

## 3\. 🌐 Multi-Language Agent Runner

Flowork's Core Kernel is a polyglot. It doesn't just run workflows; it executes **Agents**.

  * **Polyglot Execution:** Native support for **Python, JavaScript, Bash, PHP, Perl, and Ruby**.
  * **Seamless Integration:** Run legacy scripts alongside modern AI agents in the same pipeline.

## 4\. 🔌 OS-Native Triggering

Leverage your local machine as a sensor for your agents.

  * **File System Watchers:** Trigger agents instantly upon local file changes.
  * **Process Monitoring:** Initiate tasks based on OS-level events or sophisticated Cron schedules.

## 5\. 🧠 AI Powerhouse & Developer Tools

Flowork turns your local machine into a private AI R&D lab.

  * **Local AI Support:** Run *on-premise* models (llama-cpp-python, Stable Diffusion) without leaking data to the cloud.
  * **AI Analyzer:** Built-in intelligence to analyze your workflows and suggest optimizations.
  * **Component Factory:** Rapidly create custom Modules, Triggers, and Tools.

## 6\. 🔗 Collaboration & Resource Sharing

  * **Engine Sharing:** securely share access to your local Engine with remote users under strict permission control. **One *Engine* can serve multiple *Users***.
  * **Preset Sharing:** Share your agent templates with the community.

## 7\. 🛠️ Debugging and Diagnostics

  * **Time Traveler Debugger:** Inspect the full state (*variables* and *payload*) **after every node** execution.
  * **System Integrity Engine:** Automatically verifies that your core files are tamper-proof.

## 8\. ⚙️ Quick Installation & Setup Guide (Docker)

Get your Agent OS running in 5 minutes.

### Prerequisites
* Docker Desktop (or Docker Engine)
* Python 3.11+ (for initial setup script)

### Installation Steps

1.  **Generate Environment:** Create your unique Engine ID and **Admin Private Key**.
    ```bash
    python generate_env.py
    ```

2.  **Ignition:** Launch the stack.
    ```bash
    docker-compose up -d
    ```

3.  **Retrieve Key:** Get your login key from the logs.
    ```bash
    docker-compose logs flowork_gateway | grep "PRIVATE KEY"
    ```

*(See full documentation for Cloudflare Tunnel setup to enable global access)*

## 🗺️ Roadmap (Agent OS Vision)

We are currently in **V2 Era**, shifting from simple automation to a full **Autonomous Agent OS**.

* **Phase 1 (Current):** Hardening security, rate-limiting, and observability.
* **Phase 2:** Implementing **Episodic Memory** so agents can learn from past job outcomes.
* **Phase 3:** **Swarm Mini** for coordinated multi-agent tasks on local hardware.
* *See `ROADMAP.md` for the detailed battle plan.*

## 9\. 🌐 Resources & Community

Join the resistance. We are building the future of sovereign automation.

| Platform | Link |
| :--- | :--- |
| **Website** | [https://flowork.cloud](https://flowork.cloud) |
| **Documentation** | [https://docs.flowork.cloud/](https://docs.flowork.cloud/) |
| **GitHub** | [Repo Link](https://github.com/flowork-dev/Visual-AI-Workflow-Automation-Platform) |
| **Telegram** | [Join Chat](https://t.me/FLOWORK_AUTOMATION) |
| **Discord** | [Server Invite](https://discord.gg/Gv7h5fWZY) |