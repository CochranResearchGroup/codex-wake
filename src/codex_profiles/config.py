from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import tomllib


DEFAULT_SHARED_LINKS = (
    "config.toml",
    "skills",
    "rules",
)


DEFAULT_PROJECTED_LINKS = (
    "auth.json",
    "config.toml",
    "skills",
    "rules",
)


def account_environment(home: Path, profile: str) -> dict[str, str]:
    """Select the saved account instead of an inherited native login override."""
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "CODEX_AUTH_TOKEN", "CODEX_THREAD_ID"):
        env.pop(key, None)
    env["CODEX_HOME"] = str(home)
    env["CODEX_PROFILE_NAME"] = profile
    return env


@dataclass(slots=True)
class ProfileMeta:
    label: str | None = None
    owner: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class Settings:
    state_root: Path
    source_root: Path
    selection_mode: str = "launcher"
    check_upstream_releases: bool = True
    shared_dir_name: str = "shared"
    account_prefix: str = "codex-"
    shared_links: tuple[str, ...] = field(default_factory=lambda: DEFAULT_SHARED_LINKS)
    projected_links: tuple[str, ...] = field(default_factory=lambda: DEFAULT_PROJECTED_LINKS)
    default_profile: str | None = None
    aliases: dict[str, str] = field(default_factory=dict)
    known_profiles: tuple[str, ...] = ()
    profile_meta: dict[str, ProfileMeta] = field(default_factory=dict)

    @property
    def shared_root(self) -> Path:
        return self.state_root / self.shared_dir_name

    @property
    def current_profile_path(self) -> Path:
        return self.shared_root / ".current-profile"

    def resolve_profile_name(self, name: str | None, env_profile: str | None = None) -> str:
        if name:
            resolved = self.aliases.get(name, name)
            return self.normalize_profile_name(resolved)
        if env_profile:
            resolved = self.aliases.get(env_profile, env_profile)
            return self.normalize_profile_name(resolved)
        current = self.current_profile()
        if current:
            return self.normalize_profile_name(current)
        if self.default_profile:
            return self.normalize_profile_name(self.default_profile)
        raise ValueError("no profile specified and no default_profile configured")

    def normalize_profile_name(self, name: str) -> str:
        return name if name.startswith(self.account_prefix) else f"{self.account_prefix}{name}"

    def account_root(self, name: str) -> Path:
        return self.state_root / self.resolve_profile_name(name)

    def denormalize_profile_name(self, name: str) -> str:
        if name.startswith(self.account_prefix):
            return name[len(self.account_prefix) :]
        return name

    def current_profile(self) -> str | None:
        if not self.current_profile_path.exists():
            return None
        value = self.current_profile_path.read_text(encoding="utf-8").strip()
        return value or None

    def current_profile_resolved(self) -> str | None:
        current = self.current_profile()
        if not current:
            return None
        return self.resolve_profile_name(current)

    def profile_details(self, name: str) -> ProfileMeta:
        return self.profile_meta.get(self.denormalize_profile_name(name), ProfileMeta())

    def configuration_view(self, name: str) -> dict[str, object]:
        """Project configuration provenance and scopes, never credential contents."""
        home = self.account_root(name)
        result: dict[str, object] = {"profile": self.resolve_profile_name(name)}
        for label, relative in (("settings", "config.toml"), ("skills", "skills"), ("rules", "rules")):
            source = (home / relative).resolve(strict=False)
            shared = (self.shared_root / relative).resolve(strict=False)
            result[label] = {"source": str(source), "shared": relative in self.shared_links and source == shared}
        config_path = home / "config.toml"
        config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
        mode = config.get("mcp_oauth_credentials_store", "auto")
        scopes = {
            "auto": "operator keyring for ordinary connectors when available; tenant-local file fallback; enterprise identity remains tenant-scoped",
            "keyring": "operator keyring for ordinary connectors; enterprise identity remains tenant-scoped",
            "file": "tenant-local OAuth file; common logins unavailable through file storage",
        }
        result["mcp"] = {"servers": sorted(config.get("mcp_servers", {})), "oauth_store": mode,
                         "identity_scope": scopes.get(mode, "unsupported credential mode"),
                         "codex_account_auth": "tenant-local; independent of MCP identity",
                         "live_refresh": "explicit; shared edits apply to subsequent launches"}
        return result


def default_settings() -> Settings:
    home = Path.home()
    return Settings(state_root=home / ".codex", source_root=home / ".codex")


def load_settings(config_path: Path | None, state_root: Path | None = None, source_root: Path | None = None) -> Settings:
    settings = default_settings()

    if config_path and config_path.exists():
        config_data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        profile_data = config_data.get("profiles", {})
        if "state_root" in profile_data:
            settings.state_root = Path(os.path.expanduser(profile_data["state_root"]))
        if "source_root" in profile_data:
            settings.source_root = Path(os.path.expanduser(profile_data["source_root"]))
        if "selection_mode" in profile_data:
            settings.selection_mode = profile_data["selection_mode"]
        if "check_upstream_releases" in profile_data:
            if type(profile_data["check_upstream_releases"]) is not bool:
                raise ValueError("check_upstream_releases must be true or false")
            settings.check_upstream_releases = profile_data["check_upstream_releases"]
        if "shared_dir_name" in profile_data:
            settings.shared_dir_name = profile_data["shared_dir_name"]
        if "account_prefix" in profile_data:
            settings.account_prefix = profile_data["account_prefix"]
        if "shared_links" in profile_data:
            settings.shared_links = tuple(profile_data["shared_links"])
        if "projected_links" in profile_data:
            settings.projected_links = tuple(profile_data["projected_links"])
        if "default_profile" in profile_data:
            settings.default_profile = profile_data["default_profile"]
        if "aliases" in profile_data:
            settings.aliases = dict(profile_data["aliases"])
        if "known_profiles" in profile_data:
            settings.known_profiles = tuple(profile_data["known_profiles"])
        meta_data = profile_data.get("meta", {})
        settings.profile_meta = {
            key: ProfileMeta(
                label=value.get("label"),
                owner=value.get("owner"),
                notes=value.get("notes"),
            )
            for key, value in meta_data.items()
        }

    if state_root is not None:
        settings.state_root = state_root
    if source_root is not None:
        settings.source_root = source_root

    if settings.selection_mode not in {"launcher", "projection"}:
        raise ValueError("profiles.selection_mode must be 'launcher' or 'projection'")

    return settings
