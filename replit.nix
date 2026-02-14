{ pkgs }:
{
  deps = [
    pkgs.python3
    pkgs.python3Packages.uvicorn
    pkgs.python3Packages.fastapi
    pkgs.python3Packages.pydantic
    pkgs.python3Packages.httpx
    pkgs.nodejs-16_x
    pkgs.nodePackages.pnpm
  ];
}
