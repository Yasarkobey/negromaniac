{ pkgs }: {
  deps = [
    pkgs.python38
    pkgs.python38Packages.pip
    pkgs.nodejs
  ];
}