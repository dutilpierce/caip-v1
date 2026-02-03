{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.nodejs_18
  ];
}
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.python3Packages.httpx
    pkgs.python3Packages.supabase
    pkgs.python3Packages.gotrue
    pkgs.python3Packages.python-dotenv
    pkgs.nodejs_18
  ];
}
