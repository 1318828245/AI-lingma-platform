import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { User } from "../types";

const TOKEN_KEY = "ailingma_access_token";
const REFRESH_KEY = "ailingma_refresh_token";
const USER_KEY = "ailingma_user";

function loadUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref(localStorage.getItem(TOKEN_KEY) || "");
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY) || "");
  const user = ref<User | null>(loadUser());

  const isLoggedIn = computed(() => !!accessToken.value);

  function setSession(token: string, refresh: string, u: User) {
    accessToken.value = token;
    refreshToken.value = refresh;
    user.value = u;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REFRESH_KEY, refresh);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
  }

  function logout() {
    accessToken.value = "";
    refreshToken.value = "";
    user.value = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  return { accessToken, refreshToken, user, isLoggedIn, setSession, logout };
});
