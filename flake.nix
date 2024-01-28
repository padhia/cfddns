{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      with nixpkgs.legacyPackages.${system};

      let
        packages.default = stdenv.mkDerivation {
          pname = "cfddns";
          version = "0.1.0";
          dontUnpack = true;

          installPhase = ''
            install -Dm755 ${./cfddns.py} $out/bin/cfddns
          '';

          meta = with lib; {
            homepage = "https://github.com/padhia/cfddns";
            description = "update Cloudflare IP address for DNS A record";
            maintainers = with maintainers; [ padhia ];
          };
        };

      in {
        inherit packages;

        devShells.default = mkShell {
          name = "cfddns";
          buildInputs = [ python3 ruff ];
        };

        apps.default.type = "app";
        apps.default.program = "${packages.default}/bin/cfddns";
      }
    );
}
