import { useSearchParams } from "next/navigation";
import { CALLBACK_URL, PLAIN_MSG } from "./mutations";
import { authorizationModel } from "~/lib/models";

function parseHashParams(hash: string) {
  const hashParams = new URLSearchParams(hash.substring(1));
  const params: Record<string, string> = {};
  hashParams.forEach((value, key) => {
    params[key] = value;
  });
  return params;
}

export function useHandleRidirectFromWallet() {
  const params = useSearchParams();
  const hashParams = parseHashParams(location.hash);

  const action = params.get("action");

  if (action === "send") {
    console.log("Received redirect from wallet!");

    const signature = hashParams.signature;

    if (signature) {
      const auth = authorizationModel.parse({
        account_id: hashParams.accountId,
        public_key: hashParams.publicKey,
        signature: hashParams.signature,
        callback_url: CALLBACK_URL,
        plainMsg: PLAIN_MSG,
      });
      localStorage.setItem("current_auth", `Bearer ${JSON.stringify(auth)}`);
    }
  }

  return params;
}
