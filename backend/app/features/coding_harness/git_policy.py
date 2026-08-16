"""Allowlisted local Git capability descriptions; no shell command construction."""
from __future__ import annotations
class GitPolicyError(ValueError):pass
def validate_git_args(action:str,args:list[str])->None:
 if action not in {"git_commit","git_push","git_diff","git_status"}:raise GitPolicyError("git action denied")
 if any(arg.startswith("-") and arg not in {"--amend"} for arg in args):raise GitPolicyError("git option denied")
 if any(".." in arg or "\x00" in arg or "/" in arg and arg.startswith("/") for arg in args):raise GitPolicyError("git path denied")
 if action=="git_push":raise GitPolicyError("push requires explicit HITL execution")
