import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { apiRequest } from "../api";

export type UserRole = "student" | "faculty" | "dean" | "principal";

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  department_id: number | null;
}

export interface Department {
  id: number;
  name: string;
  code: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: UserProfile;
}

interface AuthState {
  accessToken: string;
  user: UserProfile;
}

interface AuthContextValue {
  accessToken: string | null;
  user: UserProfile | null;
  isRestoring: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  register: (input: StudentRegistrationInput | FacultyRegistrationInput) => Promise<UserProfile>;
  logout: () => Promise<void>;
}

export interface StudentRegistrationInput {
  email: string;
  full_name: string;
  password: string;
  department_id: number;
  year: number;
  semester: number;
}

export interface FacultyRegistrationInput {
  name: string;
  email: string;
  password: string;
  department_id: number;
  subject_ids: number[];
}

const REFRESH_TOKEN_KEY = "student-success.refresh-token";
const AuthContext = createContext<AuthContextValue | null>(null);

function saveTokens(response: TokenResponse): void {
  sessionStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
}

async function requestRefresh(): Promise<TokenResponse> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    throw new Error("Your session has expired. Please sign in again.");
  }
  const response = await apiRequest<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  saveTokens(response);
  return response;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [expiresIn, setExpiresIn] = useState<number | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const restorePromise = useRef<Promise<TokenResponse> | null>(null);

  const applyTokenResponse = useCallback((response: TokenResponse) => {
    saveTokens(response);
    setAuth({ accessToken: response.access_token, user: response.user });
    setExpiresIn(response.expires_in);
  }, []);

  useEffect(() => {
    if (!sessionStorage.getItem(REFRESH_TOKEN_KEY)) {
      setIsRestoring(false);
      return;
    }

    if (!restorePromise.current) {
      restorePromise.current = requestRefresh();
    }
    let mounted = true;
    restorePromise.current
      .then((response) => {
        if (mounted) {
          applyTokenResponse(response);
        }
      })
      .catch(() => {
        sessionStorage.removeItem(REFRESH_TOKEN_KEY);
        if (mounted) {
          setAuth(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setIsRestoring(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [applyTokenResponse]);

  useEffect(() => {
    if (auth === null || expiresIn === null) {
      return;
    }
    const refreshDelay = Math.max(30_000, (expiresIn - 60) * 1000);
    const timer = window.setTimeout(() => {
      requestRefresh()
        .then(applyTokenResponse)
        .catch(() => {
          sessionStorage.removeItem(REFRESH_TOKEN_KEY);
          setAuth(null);
          setExpiresIn(null);
        });
    }, refreshDelay);
    return () => window.clearTimeout(timer);
  }, [applyTokenResponse, auth, expiresIn]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      applyTokenResponse(response);
      return response.user;
    },
    [applyTokenResponse],
  );

  const register = useCallback(
    async (input: StudentRegistrationInput | FacultyRegistrationInput) => {
      const endpoint = "subject_ids" in input ? "/auth/register/faculty" : "/auth/register";
      const response = await apiRequest<TokenResponse>(endpoint, {
        method: "POST",
        body: JSON.stringify(input),
      });
      applyTokenResponse(response);
      return response.user;
    },
    [applyTokenResponse],
  );

  const logout = useCallback(async () => {
    const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
    if (auth && refreshToken) {
      try {
        await apiRequest<void>(
          "/auth/logout",
          { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
          auth.accessToken,
        );
      } finally {
        sessionStorage.removeItem(REFRESH_TOKEN_KEY);
        setAuth(null);
        setExpiresIn(null);
      }
      return;
    }
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    setAuth(null);
    setExpiresIn(null);
  }, [auth]);

  return (
    <AuthContext.Provider
      value={{
        accessToken: auth?.accessToken ?? null,
        user: auth?.user ?? null,
        isRestoring,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}

export const portalPaths: Record<UserRole, string> = {
  student: "/student",
  faculty: "/faculty",
  dean: "/dean",
  principal: "/principal",
};

export const roleLabels: Record<UserRole, string> = {
  student: "Student",
  faculty: "Faculty",
  dean: "Dean",
  principal: "Principal",
};
