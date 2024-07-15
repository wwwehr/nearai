import { Button } from "~/components/ui/button";
import { useWalletSelector } from "~/context/WalletSelectorContext";

export function NearAccount() {
  const { selector, modal, accountId } = useWalletSelector();

  const handleSignOut = async () => {
    const w = await selector.wallet();
    await w.signOut();
  };

  return (
    <div>
      {accountId && (
        <Button
          onClick={handleSignOut}
          variant="outline"
          className="text-wrap"
          type="button"
        >
          Log out: {accountId}
        </Button>
      )}

      {!accountId && (
        <Button
          onClick={() => {
            console.log("selector", selector);

            modal.show();
          }}
          type="button"
        >
          NEAR Log In
        </Button>
      )}
    </div>
  );
}
