import { LoginRequest, LoginResponse, SignupRequest } from "@/types/entity";
import type { AxiosInstance } from "axios";

export class AuthApi {
  constructor(private http: AxiosInstance) { }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const params = new URLSearchParams();
    params.append("username", credentials.email);
    params.append("password", credentials.password);

    const { data } = await this.http.post<LoginResponse>("/auth/token", params);
    return data;
  }

  async signup(payload: SignupRequest) {
    const { data } = await this.http.post("/auth/register", payload);
    return data;
  }

  async getMe() {
    const { data } = await this.http.get("/users/me");
    return data;
  }
}
