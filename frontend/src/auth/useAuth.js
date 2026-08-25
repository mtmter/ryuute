import { useContext } from "react";
import AuthContext from "./authContext";

function useAuth() {
  const authContext = useContext(AuthContext);

  if (authContext === null) {
    throw new Error("useAuthはAuthProviderの内側で使用してください");
  }

  return authContext;
}

export default useAuth;
