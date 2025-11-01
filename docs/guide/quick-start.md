# Quick Start

This guide will walk you through creating your identity and running your first workflow in 5 minutes.

## Step 1: Create Your Identity (in Browser)

Your identity is not stored on our servers. It's a cryptographic key you own.

1.  Go to [https://flowork.cloud](https://flowork.cloud).
2.  You will be on the **Login** page. Click the link at the bottom: **"Don't have an identity? Create one"**.
3.  Click the **"Generate Secure Identity"** button.
4.  **CRITICAL:** You will be shown a **12-word recovery phrase**. Write this down and store it in a secure place (like a password manager). This is the *only* way to recover your account.
5.  Check the box confirming you have saved your phrase, and click **"Create My Identity"**.
6.  You are now logged in. Your browser has saved your Private Key locally.

## Step 2: Register Your Local Engine

Now, we link your browser GUI to the Engine running on your machine.

1.  After logging in, you will be prompted to select an engine. Click **"Go to Engine Management"**. (Or click **My Engines** in the top-right menu).
2.  Click **"Register New Engine"**.
3.  Give it a name (e.g., `My Docker PC`) and click **Register**.
4.  A popup will appear with your **Engine ID** and **Engine Token**.

## Step 3: Configure Your Local Engine

1.  Open your `C:\FLOWORK\.env` file (the file we configured during installation).
2.  Copy the `FLOWORK_ENGINE_ID` and `FLOWORK_ENGINE_TOKEN` from the GUI popup and paste them into the `.env` file, replacing the old values.

    ```env
    # C:\FLOWORK\.env
    ...
    FLOWORK_ENGINE_ID=e5b3f37e-b1b9-4cc6-bcc0-e9391fdd2cef
    FLOWORK_ENGINE_TOKEN=dev_engine_080b48fe91672c89f0de12714a2e1658
    ```

3.  Save the `.env` file.
4.  Run `2-STOP_DOCKER_(SAFE).bat` to stop your engine.
5.  Run `3-RUN_DOCKER.bat` to restart it with the new credentials.

## Step 4: Run Your First Workflow

1.  Go back to the Flowork GUI in your browser.
2.  In the **My Engines** page, your new engine (`My Docker PC`) should now appear as **Online** (it may take 30-60 seconds).
3.  Navigate to the **Designer** (from the top menu).
4.  Your engine should show as "Connected" in the bottom-left controls.
5.  Drag a `Debug Popup` node from the "Toolbox" (left sidebar) onto the canvas.
6.  Click the big green **"Run Workflow"** button in the footer.

**Congratulations!** Your browser just sent a secure command to your local engine, which executed the workflow and confirmed completion. You are now ready to build powerful automations.