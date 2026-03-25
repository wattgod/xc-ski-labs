#!/usr/bin/env python3
"""
XC Ski Labs — Deploy to SiteGround via tar+ssh

Uploads race pages, search UI, homepage, and search index
to SiteGround. Same pattern as Gravel God deploy.

Usage:
    python deploy.py --sync-pages                 # race pages to /race/
    python deploy.py --sync-homepage               # homepage to site root
    python deploy.py --sync-search                 # search UI + index to /search/
    python deploy.py --sync-index                  # race-index.json to /search/
    python deploy.py --sync-sitemap                # sitemap to site root
    python deploy.py --sync-training               # training plans to /training-plans/
    python deploy.py --sync-coaching               # coaching form to /coaching/apply/
    python deploy.py --purge-cache                 # purge SiteGround caches
    python deploy.py --deploy-all                  # everything + cache purge
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SSH_KEY = Path.home() / ".ssh" / "xcskilabs_key"


def get_ssh_credentials():
    """Return (host, user, port) or None with warning."""
    host = os.environ.get("GL_SSH_HOST") or os.environ.get("SSH_HOST")
    user = os.environ.get("GL_SSH_USER") or os.environ.get("SSH_USER")
    port = os.environ.get("GL_SSH_PORT") or os.environ.get("SSH_PORT", "18765")

    if not all([host, user]):
        print("  SSH credentials not set. Required env vars:")
        print("   GL_SSH_HOST, GL_SSH_USER (optional: GL_SSH_PORT)")
        return None
    if not SSH_KEY.exists():
        print(f"  SSH key not found: {SSH_KEY}")
        return None
    return host, user, port


def get_remote_base():
    """Return the remote public_html path."""
    return os.environ.get(
        "GL_REMOTE_BASE",
        "~/www/xcskilabs.com/public_html"
    )


def _ssh_run(host, user, port, cmd, timeout=30):
    """Run a command over SSH. Returns (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            [
                "ssh", "-i", str(SSH_KEY), "-p", port,
                f"{user}@{host}", cmd,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timed out"
    except Exception as e:
        return False, "", str(e)


def _scp_upload(host, user, port, local_path, remote_path, timeout=30):
    """Upload a single file via SCP."""
    try:
        subprocess.run(
            [
                "scp", "-i", str(SSH_KEY), "-P", port,
                str(local_path), f"{user}@{host}:{remote_path}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  SCP failed: {e.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print("  SCP timed out")
        return False


def _tar_ssh_upload(host, user, port, local_dir, remote_dir, timeout=300):
    """Upload a directory via tar+ssh pipe."""
    items = [p.name for p in sorted(Path(local_dir).iterdir())]
    if not items:
        print("  No files to upload")
        return False

    tar_cmd = ["tar", "-cf", "-", "-C", str(local_dir)] + items
    ssh_cmd = [
        "ssh", "-i", str(SSH_KEY), "-p", port,
        f"{user}@{host}",
        f"tar -xf - -C {remote_dir}",
    ]

    try:
        tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
        ssh_proc = subprocess.Popen(
            ssh_cmd, stdin=tar_proc.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        tar_proc.stdout.close()
        stdout, stderr = ssh_proc.communicate(timeout=timeout)

        if ssh_proc.returncode != 0:
            print(f"  tar+ssh failed: {stderr.decode().strip()}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  Upload timed out")
        tar_proc.kill()
        ssh_proc.kill()
        return False
    except Exception as e:
        print(f"  Upload error: {e}")
        return False


# ── Sync Functions ────────────────────────────────────────────


def sync_pages(pages_dir=None):
    """Upload race pages to /race/ on SiteGround via tar+ssh.

    Uses {slug}/index.html directory structure from the output dir.
    """
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    pages_path = Path(pages_dir) if pages_dir else PROJECT_ROOT / "output"
    if not pages_path.exists():
        print(f"  Pages directory not found: {pages_path}")
        return False

    remote_base = f"{get_remote_base()}/race"

    # Find all slug directories with index.html
    slug_dirs = [
        d for d in sorted(pages_path.iterdir())
        if d.is_dir() and d.name != "search" and (d / "index.html").exists()
    ]

    if not slug_dirs:
        print(f"  No race page directories found in {pages_path}")
        return False

    # Create remote directory
    ok, _, err = _ssh_run(host, user, port,
                          f"mkdir -p {remote_base} && chmod 755 {remote_base}")
    if not ok:
        print(f"  Failed to create remote directory: {err}")
        return False

    # Build staging directory with just the slug/index.html dirs
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for slug_dir in slug_dirs:
            dst = tmpdir / slug_dir.name
            shutil.copytree(slug_dir, dst)

        page_count = len(slug_dirs)
        print(f"  Uploading {page_count} race pages via tar+ssh...")

        if not _tar_ssh_upload(host, user, port, tmpdir, remote_base):
            return False

    # Fix permissions
    _ssh_run(host, user, port, f"chmod -R 755 {remote_base}")

    # Post-deploy validation: count remote index.html files
    ok, stdout, _ = _ssh_run(
        host, user, port,
        f"find {remote_base} -name index.html | wc -l",
        timeout=30,
    )
    if ok and stdout.strip().isdigit():
        remote_count = int(stdout.strip())
        if remote_count != page_count:
            print(f"  WARNING: expected {page_count} index.html files on remote, found {remote_count}")
        else:
            print(f"  Verified: {remote_count} index.html files on remote")

    print(f"  Deployed {page_count} race pages to /race/")
    return True


def sync_homepage(homepage_file=None):
    """Upload homepage to site root as index.html."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    homepage = Path(homepage_file) if homepage_file else PROJECT_ROOT / "output" / "index.html"
    if not homepage.exists():
        print(f"  Homepage not found: {homepage}")
        return False

    remote_base = get_remote_base()

    # Create a homepage directory structure
    # Deploy as /index.html at the root (or alongside WordPress)
    # Since WordPress is at the root, we deploy to /races/ or similar
    # Or if this IS the primary domain, straight to root
    ok, _, err = _ssh_run(host, user, port, f"mkdir -p {remote_base}")
    if not ok:
        print(f"  Failed to create remote directory: {err}")
        return False

    if _scp_upload(host, user, port, homepage, f"{remote_base}/index.html"):
        print(f"  Deployed homepage to /")
        return True
    return False


def sync_search():
    """Upload search UI (HTML + JS + index) to /search/ on SiteGround."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    web_dir = PROJECT_ROOT / "web"
    remote_search = f"{get_remote_base()}/search"

    ok, _, err = _ssh_run(host, user, port,
                          f"mkdir -p {remote_search} && chmod 755 {remote_search}")
    if not ok:
        print(f"  Failed to create /search/ directory: {err}")
        return False

    files = [
        (web_dir / "nordic-lab-search.html", f"{remote_search}/index.html"),
        (web_dir / "nordic-lab-search.js", f"{remote_search}/nordic-lab-search.js"),
        (web_dir / "race-index.json", f"{remote_search}/race-index.json"),
    ]

    success = 0
    for local, remote in files:
        if not local.exists():
            print(f"  Missing: {local.name}")
            continue
        if _scp_upload(host, user, port, local, remote):
            success += 1

    if success == len(files):
        print(f"  Deployed search UI ({success} files) to /search/")
        return True

    print(f"  FAILED: partial deploy {success}/{len(files)} files")
    return success == len(files)


def sync_index():
    """Upload just the race-index.json to /search/."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    index_file = PROJECT_ROOT / "web" / "race-index.json"
    if not index_file.exists():
        print(f"  Index file not found: {index_file}")
        return False

    remote = f"{get_remote_base()}/search/race-index.json"
    if _scp_upload(host, user, port, index_file, remote):
        print(f"  Deployed race-index.json to /search/")
        return True
    return False


def sync_sitemap():
    """Upload sitemap.xml to site root."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    sitemap = PROJECT_ROOT / "web" / "sitemap.xml"
    if not sitemap.exists():
        print("  sitemap.xml not found — generate it first")
        return False

    remote = f"{get_remote_base()}/sitemap.xml"
    if _scp_upload(host, user, port, sitemap, remote):
        print("  Deployed sitemap.xml")
        return True
    return False


def sync_training():
    """Upload training plans page to /training-plans/ on SiteGround."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    training_dir = PROJECT_ROOT / "output" / "training-plans"
    training_file = training_dir / "index.html"
    if not training_file.exists():
        print(f"  Training plans page not found: {training_file}")
        print("  Run: python wordpress/generate_training_plans.py")
        return False

    remote_dir = f"{get_remote_base()}/training-plans"
    ok, _, err = _ssh_run(host, user, port,
                          f"mkdir -p {remote_dir} && chmod 755 {remote_dir}")
    if not ok:
        print(f"  Failed to create /training-plans/ directory: {err}")
        return False

    if _scp_upload(host, user, port, training_file, f"{remote_dir}/index.html"):
        print("  Deployed training plans page to /training-plans/")
        return True
    return False


def sync_coaching():
    """Upload coaching intake form to /coaching/apply/ on SiteGround."""
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    coaching_file = PROJECT_ROOT / "output" / "coaching" / "apply" / "index.html"
    if not coaching_file.exists():
        print(f"  Coaching intake form not found: {coaching_file}")
        print("  Run: python wordpress/generate_coaching_apply.py")
        return False

    remote_dir = f"{get_remote_base()}/coaching/apply"
    ok, _, err = _ssh_run(host, user, port,
                          f"mkdir -p {remote_dir} && chmod 755 {remote_dir}")
    if not ok:
        print(f"  Failed to create /coaching/apply/ directory: {err}")
        return False

    if _scp_upload(host, user, port, coaching_file, f"{remote_dir}/index.html"):
        print("  Deployed coaching intake form to /coaching/apply/")
        return True
    return False


def purge_cache():
    """Purge SiteGround caches.

    Tries wp-cli. If unavailable (static site), prints manual instructions.
    Returns True either way (non-fatal).
    """
    ssh = get_ssh_credentials()
    if not ssh:
        return False
    host, user, port = ssh

    wp_path = get_remote_base()

    ok, stdout, stderr = _ssh_run(
        host, user, port,
        f"wp --path={wp_path} sg purge 2>&1",
        timeout=30,
    )
    if ok:
        print("  SiteGround cache purged (wp-cli)")
        return True

    print("  Cache purge requires manual action: go to SiteGround Site Tools → Speed → Caching → Flush Cache")
    return True  # Non-fatal — pages are still deployed


def deploy_all():
    """Deploy everything and purge cache."""
    print("XC Ski Labs — Full Deploy")
    print("=" * 40)

    steps = [
        ("Homepage", sync_homepage),
        ("Search UI", sync_search),
        ("Race Pages", sync_pages),
        ("Training Plans", sync_training),
        ("Coaching Form", sync_coaching),
        ("Sitemap", sync_sitemap),
        ("Cache Purge", purge_cache),
    ]

    results = []
    for name, fn in steps:
        print(f"\n[{name}]")
        ok = fn()
        results.append((name, ok))

    print("\n" + "=" * 40)
    print("Deploy Summary:")
    for name, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status}")

    return all(ok for _, ok in results)


# ── CLI ───────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy XC Ski Labs race pages to SiteGround"
    )
    parser.add_argument(
        "--sync-pages", action="store_true",
        help="Upload race pages to /race/ via tar+ssh"
    )
    parser.add_argument(
        "--pages-dir", default=None,
        help="Path to pages directory (default: output/)"
    )
    parser.add_argument(
        "--sync-homepage", action="store_true",
        help="Upload homepage to site root via SCP"
    )
    parser.add_argument(
        "--homepage-file", default=None,
        help="Path to homepage HTML (default: output/index.html)"
    )
    parser.add_argument(
        "--sync-search", action="store_true",
        help="Upload search UI + index to /search/ via SCP"
    )
    parser.add_argument(
        "--sync-index", action="store_true",
        help="Upload race-index.json to /search/ via SCP"
    )
    parser.add_argument(
        "--sync-sitemap", action="store_true",
        help="Upload sitemap.xml to site root"
    )
    parser.add_argument(
        "--sync-training", action="store_true",
        help="Upload training plans page to /training-plans/"
    )
    parser.add_argument(
        "--sync-coaching", action="store_true",
        help="Upload coaching intake form to /coaching/apply/"
    )
    parser.add_argument(
        "--purge-cache", action="store_true",
        help="Purge all SiteGround caches"
    )
    parser.add_argument(
        "--deploy-all", action="store_true",
        help="Deploy everything (pages, search, training, coaching) + purge cache"
    )

    args = parser.parse_args()

    if args.deploy_all:
        deploy_all()
    else:
        ran = False
        if args.sync_pages:
            sync_pages(args.pages_dir)
            ran = True
        if args.sync_homepage:
            sync_homepage(args.homepage_file)
            ran = True
        if args.sync_search:
            sync_search()
            ran = True
        if args.sync_index:
            sync_index()
            ran = True
        if args.sync_sitemap:
            sync_sitemap()
            ran = True
        if args.sync_training:
            sync_training()
            ran = True
        if args.sync_coaching:
            sync_coaching()
            ran = True
        if args.purge_cache:
            purge_cache()
            ran = True

        if not ran:
            parser.error(
                "Provide a sync flag (--sync-pages, --sync-homepage, etc.) or --deploy-all"
            )
