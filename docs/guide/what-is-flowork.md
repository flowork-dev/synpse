# What is Flowork?

Flowork is a **hybrid, self-hosted visual automation platform** designed for building, training, and commanding AI agents and complex workflows.

It provides a secure, powerful alternative to cloud-only services like Zapier or Make.com, with a strong focus on **data privacy** and **user ownership**.

## The Core Philosophy: Your Identity, Your Data, Your Engine

Flowork operates on three core principles:

1.  **Your Identity:** You don't create an "account" in the traditional sense. You generate a cryptographic **Private Key** (like a crypto wallet). This key *is* your identity. It's stored only on your device, giving you full control.
2.  **Your Data:** Your workflows, presets, and configuration data are stored locally on your machine using a secure "Flow-Chain" system (hashed and signed). Your data **never** leaves your control.
3.  **Your Engine:** You run the Flowork Core Engine on your own hardware (PC, server, or Docker). The engine connects to our Gateway, but all processing, AI inference, and data handling happen **locally** on your machine.

## How It Works

The architecture is split into three main parts:

* **The GUI (flowork.cloud):** The visual designer you use in your browser. It's hosted by us on Cloudflare Pages so you never have to install or update it.
* **The Gateway (api.flowork.cloud):** A lightweight cloud service that handles identity verification (checking your cryptographic signatures) and manages engine connections. It *never* sees your workflow data.
* **The Core Engine (Your PC):** The powerful backend you run locally. It connects securely to the Gateway, receives your signed commands from the GUI, and performs all the work (running workflows, connecting to APIs, executing AI models).

This hybrid model gives you the convenience of a web app with the power and security of a locally-hosted application.