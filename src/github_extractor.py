import os
import sys
from collections import Counter
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import GitHubSignals, CodeQuality
from github import Github, Auth


HYGIENE_MARKERS = {
    "readme":   ["readme.md", "readme.rst", "readme.txt", "readme"],
    "license":  ["license", "license.md", "license.txt"],
    "tests":    ["tests", "test", "spec", "__tests__"],
    "ci":       [".github", ".gitlab-ci.yml", ".circleci", ".travis.yml"],
    "deps":     ["requirements.txt", "package.json", "pyproject.toml"],
    "gitignore":[".gitignore"],
}

GENERIC_COMMIT_MSGS = {
    "fix", "update", "changes", "wip", "stuff",
    "asdf", "commit", "test", "minor", "."
}

def _root_names(repo) -> set:
    try:
        return {c.name.lower() for c in repo.get_contents("")}
    except Exception:
        return set()
    

def _hygiene_for_repo(names: set) -> dict:
    found = {}
    for key, candidates in HYGIENE_MARKERS.items():
        found[key] = any(
            name == c or name.startswith(c.split(".")[0])
            for name in names
            for c in candidates
        )
    return found


def _commit_quality(repo, limit: int = 30) -> float:
    try:
        msgs = [c.commit.message.split("\n")[0].strip()
                for c in repo.get_commits()[:limit]]
    except Exception:
        return 0.0
    if not msgs:
        return 0.0
    good = sum(1 for m in msgs
               if len(m.split()) >= 3
               and m.lower().strip(". ") not in GENERIC_COMMIT_MSGS)
    return round(good / len(msgs), 2)


def extract_github_signals(username: str, token: str = None,
                           top_n: int = 5) -> GitHubSignals:
    sig = GitHubSignals(username=username)
    try:
        client = Github(auth=Auth.Token(token)) if token else Github()
        user = client.get_user(username)
        repos = list(user.get_repos())
    except Exception as e:
        sig.note = f"could not fetch profile: {e}"
        return sig

    if not repos:
        sig.note = "profile has no public repos"
        return sig

    originals = [r for r in repos if not r.fork]
    sig.active_repos = len(originals)
    sig.original_ratio = round(len(originals) / len(repos), 2)

    lang_bytes = Counter()
    for r in originals:
        try:
            for lang, b in r.get_languages().items():
                lang_bytes[lang] += b
        except Exception:
            continue
    total = sum(lang_bytes.values()) or 1
    sig.languages = {l: round(b / total, 2)
                     for l, b in lang_bytes.most_common(6)}

    top = sorted(originals,
                 key=lambda r: (r.stargazers_count, r.size),
                 reverse=True)[:top_n]

    hygiene_hits = Counter()
    topics = set()
    for r in top:
        names = _root_names(r)
        for k, present in _hygiene_for_repo(names).items():
            if present:
                hygiene_hits[k] += 1
        try:
            topics.update(r.get_topics())
        except Exception:
            pass

    sig.inferred_skills = sorted(
        set(list(sig.languages.keys()) + list(topics)))
    sig.commit_quality = _commit_quality(top[0]) if top else 0.0

    tests_present = round(
        hygiene_hits["tests"] / len(top), 2) if top else 0.0
    combined = (
        2.0 * tests_present +
        1.0 * sig.commit_quality +
        0.5 * (hygiene_hits["ci"] / len(top) if top else 0) +
        0.5 * (hygiene_hits["readme"] / len(top) if top else 0)
    )
    sig.code_quality = CodeQuality(
        tests_present=tests_present,
        avg_complexity="unknown",
        score=round(max(1.0, min(5.0, combined)), 1),
    )
    return sig


if __name__ == "__main__":
    import json
    from src.contracts import asdict
    username = sys.argv[1] if len(sys.argv) > 1 else "torvalds"
    token = os.environ.get("GITHUB_TOKEN")
    result = extract_github_signals(username, token=token)
    print(json.dumps(asdict(result), indent=2))