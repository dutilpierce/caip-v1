{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.httpx
    pkgs.python311Packages.supabase
    pkgs.python311Packages.gotrue
    pkgs.python311Packages.python-dotenv
    pkgs.nodejs_18
  ];
}
