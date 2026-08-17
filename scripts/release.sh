#!/usr/bin/env bash
# Build and publish a tagged GitHub release from staged changes or current HEAD.

set -euo pipefail

die() {
    echo "error: $*" >&2
    exit 1
}

version="${1:-}"
[[ -n "$version" ]] || die "usage: $0 VERSION (for example: $0 0.1.1)"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.](dev|post)[0-9]+)?$ ]] || die "VERSION must be a PEP 440 release version"

project_version="$(sed -nE 's/^version = "([^"]+)"/\1/p' pyproject.toml)"
package_version="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' src/spirit1/__init__.py)"
[[ "$project_version" == "$version" ]] || die "pyproject.toml has version $project_version, not $version"
[[ "$package_version" == "$version" ]] || die "src/spirit1/__init__.py has version $package_version, not $version"

git diff --quiet || die "stage or discard unstaged changes before releasing"
commit_staged=false
if ! git diff --cached --quiet; then
    commit_staged=true
fi

tag="v$version"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && die "tag $tag already exists"
command -v gh >/dev/null || die "GitHub CLI (gh) is required"
gh auth status >/dev/null || die "authenticate the GitHub CLI with: gh auth login"

if [[ -d dist ]] && find dist -type f -print -quit | grep -q .; then
    die "dist/ contains existing artifacts; remove or archive them before releasing"
fi

if $commit_staged; then
    release_action="commit the staged changes, tag"
else
    release_action="tag the current HEAD (no new commit)"
fi
echo "This will test, $release_action $tag, push to origin, and create a GitHub release."
read -r -p "Continue? [y/N] " answer
[[ "$answer" =~ ^[Yy]$ ]] || exit 0

PYTHONPATH=src python -m unittest discover -s tests -q
rm -rf build src/spirit1.egg-info
python -m build
python -m twine check --strict dist/*

if $commit_staged; then
    git commit -m "Release $version"
fi
git tag -a "$tag" -m "Release $version"
git push origin HEAD
git push origin "$tag"
gh release create "$tag" dist/* --title "$tag" --generate-notes

echo "Published $tag"
