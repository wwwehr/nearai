"use client";

import { WalletSelectorContextProvider } from "~/context/WalletSelectorContext";
import { Chat } from "./_components/chat";

export default function Home() {
  return (
    <main>
      <WalletSelectorContextProvider>
        <Chat />
      </WalletSelectorContextProvider>
    </main>
  );
}
