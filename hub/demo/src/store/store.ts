import { type z } from "zod";
import { create, type StateCreator } from "zustand";
import { persist, devtools } from "zustand/middleware";
import { authorizationModel } from "~/lib/models";

export type IStore = AuthActions & AuthState;

export interface AuthState {
  auth: z.infer<typeof authorizationModel> | null;
  current_nonce: string | null;
}

export interface AuthActions {
  setAuthValue: (authValue: z.infer<typeof authorizationModel>) => void;
  setAuthValueRaw: (authValue: string) => void;
  setCurrentNonce: (nonce: string) => void;
  isAuthenticated: () => boolean;
  clearAuth: () => void;
  toBearer: () => string;
}

export const createAuthStore: StateCreator<
  AuthState & AuthActions,
  [],
  [],
  AuthState & AuthActions
> = (set, get) => ({
  auth: null,
  current_nonce: null,
  setAuthValue: (auth: z.infer<typeof authorizationModel>) => {
    set({ auth: auth });
  },
  setAuthValueRaw: (authValue: string) => {
    if (authValue.startsWith("Bearer ")) {
      authValue = authValue.substring("Bearer ".length);
    }
    const auth = authorizationModel.parse(JSON.parse(authValue));
    set({ auth: auth });
  },
  isAuthenticated: () => {
    return !!get().auth;
  },
  clearAuth: () => {
    set({ auth: null, current_nonce: null });
  },
  toBearer: () => {
    if (!get().auth) {
      return "";
    }
    return `Bearer ${JSON.stringify(get().auth)}`;
  },
  setCurrentNonce: (nonce: string) => {
    set({ current_nonce: nonce });
  },
});

const usePersistingStore = create<IStore>()(
  devtools(
    persist(
      (...a) => ({
        ...createAuthStore(...a),
      }),
      { name: "store" },
    ),
  ),
);

export default usePersistingStore;
