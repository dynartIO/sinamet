import os

from pathlib import Path

import tomllib

from typing import Any


class SinametConfig:
    def __init__(self) -> None:
        self.current_environref: str = "_"
        self.configs: dict[str, dict[str, str | None]] = {}
        self.config_file: dict[str, Any] = self.init_config_file()

    def __getitem__(self, key: str) -> str | None:
        try:
            return self.configs[self.current_environref][key]
        except KeyError:
            return self.configs["_"][key]

    def __setitem__(self, key: str, value: str) -> None:
        if self.current_environref not in self.configs:
            self.configs[self.current_environref] = {}
        self.configs[self.current_environref][key] = value

    def __contains__(self, item: str) -> bool:
        if self.current_environref not in self.configs:
            return False
        return item in self.configs[self.current_environref]

    def get(self, key: str, default: Any | None = None) -> Any | None:
        try:
            return self[key]
        except KeyError:
            return default

    def init_key(self,
                 key: str,
                 value: str | None = None,
                 environref: str | None = None,
                 verbose: bool = False) -> str | None:
        if not environref:
            environref = self.current_environref
        if environref not in self.configs:
            self.configs[environref] = {}
        if value is None:
            value = self.find_key(key, environref, verbose=verbose)
        if value or not self.configs[environref].get(key):
            self.configs[environref][key] = value
        return value

    def init_db(self,
                environref: str | None = None,
                verbose: bool = False,
                **kwargs: str
                ) -> str:
        if not environref:
            environref = self.current_environref
        if environref not in self.configs:
            self.configs[environref] = {}

        coredb_path = self.find_key('COREDB_PATH', environref, kwargs, verbose)
        if coredb_path:
            if verbose:
                print(f"COREDB_PATH='{coredb_path}'")
            self.configs[environref]['COREDB_PATH'] = coredb_path
            return coredb_path

        keys = [
                "COREDB_NAME",
                "COREDB_USER",
                "COREDB_PASS",
                "COREDB_HOST",
                "COREDB_PORT",
        ]
        for key in keys:
            value = self.find_key(key, environref, kwargs, verbose)
            if value is not None:
                self.configs[environref][key] = value
            if not self.configs[environref].get(key):
                raise KeyError(f"Could not find a value for {key}.")

        coredb_path = ("postgresql://"
                       f"{self.configs[environref]['COREDB_USER']}"
                       f":{self.configs[environref]['COREDB_PASS']}"
                       f"@{self.configs[environref]['COREDB_HOST']}"
                       f":{self.configs[environref]['COREDB_PORT']}"
                       f"/{self.configs[environref]['COREDB_NAME']}")
        self.configs[environref]["COREDB_PATH"] = coredb_path

        if verbose:
            print(f"COREDB_PATH='{coredb_path}'")
        return coredb_path

    def find_key(self,
                 key: str,
                 environref: str,
                 kwargs: dict[str, str] = {},
                 verbose: bool = False
                 ) -> str | None:
        """
        Ordre de priorité de recherche:
            - kwargs -> sans prefix ET sans environref
            - os.environ -> avec prefix ET avec ou sans environref
            - config file -> avec ou sans environref
        """
        if verbose:
            print(f"find_key: {key=}")
            print(">>>>> ", end="")

        # Search in kwargs
        if value := kwargs.get(key):
            if verbose:
                print(f"in kwargs: {key}='{value}'")
            return value

        # Search in environment variables
        if value := os.getenv(f"SINAMET_{key}_{environref}"):
            if verbose:
                print(f"in os.environ: SINAMET_{key}_{environref}='{value}'")
            return value
        if value := os.getenv(f"SINAMET_{key}"):
            if verbose:
                print(f"in os.environ: SINAMET_{key}='{value}'")
            return value

        # Search in config file
        current_env = os.getenv('SINAMET_CURRENT_ENV') or self.config_file.get('current_env')
        if current_env in self.config_file:
            if (value := self.config_file[current_env].get(key)):
                if verbose:
                    print(f"in config file in {current_env} table: {key}='{value}'")
                return value
        if value := self.config_file.get(key):
            if verbose:
                print(f"in config file: {key}='{value}'")
            return value
        if verbose:
            print(f"Key '{key}' not found.")
        return None

    @staticmethod
    def init_config_file() -> dict[str, Any]:
        """
        Note: FutureDev
            Envisager une recherche avec des chemins absolus ou $PYTHONPATH.
        """
        path = Path.cwd()
        while path != path.parent:
            config_path = path / 'sinamet_config.toml'
            path = path.parent

            if not config_path.is_file() or not os.access(config_path, os.R_OK):
                continue

            with open(config_path, 'rb') as f:
                return tomllib.load(f)
        return {}


config = SinametConfig()
