# NEAR Login 


The NEAR Login feature accommodates various authentication scenarios, simplifying the process of signing NearAI requests using your NEAR Account.

## Scenarios

### 1. Web Login

This scenario sets up a local server on the user's machine. A `callbackUrl` is created to handle the response, and the user is redirected to `auth.near.ai`. The authentication signature is then saved upon receiving the callback. This is the simplest option for logging in from a machine where you are already signed in with your NEAR account, such as in a web browser.

**Command:**
```bash
nearai login
```

### 2. Remote Web Login
In this scenario, a login link to `auth.near.ai` is generated without a callbackUrl. The NearAI CLI will display instructions to complete the login process. This option is convenient if you haven't used your NEAR account on the current machine but can copy the authorization link, complete the authorization on another machine, and then return to the original machine to execute the command for finalizing the login.

**Command:**
```bash
nearai login --remote
```

### 3. Login with NEAR Account ID Only
If you have previously logged in with a NEAR account using near-cli and have NEAR account credentials stored in the `~/.near-credentials/mainnet directory`, you can generate a signature and save the authentication data based on the stored NEAR keys.

**Command:**:
```bash
nearai login --accountId name.near
```

### 4. Login with Account ID and Private Key
Similar to the previous scenario, but allows for manual entry of the private key. This is useful if you want to authenticate without relying on stored credentials.

**Command:**:

```bash
nearai login --accountId name.near --privateKey key
```

## Getting Started

* Install the [NearAI CLI](https://github.com/nearai/nearai): you can install it by following the instructions in the NearAI CLI documentation.

* Choose Your Login Scenario: Depending on your needs, use one of the commands above to Login with NEAR.

* Follow the Prompts: Follow any additional prompts or instructions provided by the NearAI CLI during the authentication process.

## Login Status

To verify the current login status, you can use the following command:

```bash
nearai login status
```