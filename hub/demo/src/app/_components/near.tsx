import { Button } from "~/components/ui/button";
import {
  CALLBACK_URL,
  NONCE,
  RECIPIENT,
  useChallengeRequest,
} from "~/hooks/mutations";

export function NearLogin() {
  const challengeMut = useChallengeRequest();

  const requestSignature = async () => {
    const challenge = await challengeMut.mutateAsync();
    console.log("challenge", challenge);

    const urlParams = new URLSearchParams({
      message: challenge,
      recipient: RECIPIENT,
      nonce: NONCE,
      callbackUrl: CALLBACK_URL,
    });

    window.location.replace(`https://auth.near.ai/?${urlParams.toString()}`);
  };

  return (
    <div>
      <Button
        onClick={async () => {
          await requestSignature();
        }}
        className="w-full"
        type="button"
      >
        NEAR Log In
      </Button>
    </div>
  );
}
