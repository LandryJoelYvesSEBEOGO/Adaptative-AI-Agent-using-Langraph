import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchSession, login, logout, register } from "@/api/endpoints";
import type { User } from "@/api/types";

export const SESSION_KEY = ["session"] as const;

/** Utilisateur connecté (`null` si anonyme), restauré depuis le cookie de session. */
export function useSession() {
  return useQuery({
    queryKey: SESSION_KEY,
    queryFn: fetchSession,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onSuccess: (user: User) => queryClient.setQueryData(SESSION_KEY, user),
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password, name }: { email: string; password: string; name: string }) =>
      register(email, password, name),
    onSuccess: (user: User) => queryClient.setQueryData(SESSION_KEY, user),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      // données d'un autre utilisateur : tout le cache est jeté
      queryClient.clear();
      queryClient.setQueryData(SESSION_KEY, null);
    },
  });
}
