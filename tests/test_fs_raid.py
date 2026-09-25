"""Exercise installer functions without sourcing destructive entry points.

Run with: python3 -m unittest discover -s tests -v
Commands that could alter disks or install packages are replaced with recorders.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOST = (ROOT / "reinstall.sh").read_text()
LIVE = (ROOT / "trans.sh").read_text()
SHELLS = [("bash", ["bash"])]
if shutil.which("busybox"):
    SHELLS.append(("ash", ["busybox", "ash"]))


def function(source, name):
    match = re.search(r"(?m)^( *)" + re.escape(name) + r"\(\) \{\n", source)
    if not match:
        raise AssertionError(f"Missing function {name}")
    end = re.search(r"(?m)^" + re.escape(match.group(1)) + r"\}$", source[match.end():])
    if not end:
        raise AssertionError(f"Missing closing brace for {name}")
    return source[match.start():match.end() + end.end()] + "\n"


def definitions(source, names):
    return "".join(function(source, name) for name in names)


STUBS = '''
error_and_exit() { printf '%s\\n' "$*" >&2; exit 97; }
info() { :; }
warn() { :; }
'''


class ShellTests(unittest.TestCase):
    def run_shell(self, code, args=(), shell=None, env=None):
        return subprocess.run((shell or ["bash"]) + ["-ec", STUBS + code, "test", *args],
                              text=True, capture_output=True, timeout=10,
                              env=dict(os.environ, **(env or {})))

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_rejected(self, result, message):
        self.assertEqual(result.returncode, 97, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)


SAFETY_NAMES = ["is_fs_options_identity_safe", "is_fs_topology_section_safe",
                "is_fs_options_topology_safe", "is_fs_options_format_safe",
                "is_ext4_options_fstype_safe", "is_xfs_metadata_options_v5_safe",
                "is_xfs_options_v5_safe"]


class FilesystemTests(ShellTests):
    def test_shared_validators_match(self):
        for name in SAFETY_NAMES:
            self.assertEqual(function(HOST, name), function(LIVE, name), name)

    def test_host_and_live_reject_unsafe_options(self):
        cases = [
            ("ext4", "-E offset=1048576", "offset"),
            ("ext4", "-qEoffset=1048576", "offset"),
            ("ext4", "-E=lazy_itable_init=0,offset=1024", "offset"),
            ("ext4", "-E offset=0", "offset"),
            ("ext4", "-n", "complete filesystem"),
            ("ext4", "-qn", "complete filesystem"),
            ("ext4", "-S", "complete filesystem"),
            ("ext4", "-V", "complete filesystem"),
            ("xfs", "-N", "complete filesystem"),
            ("xfs", "-qN", "complete filesystem"),
            ("xfs", "-V", "complete filesystem"),
            ("ext4", "--", "complete filesystem"),
            ("ext4", "-L another-root", "label or UUID"),
            ("ext4", "-qU random", "label or UUID"),
            ("ext4", "-t ext2", "filesystem type"),
            ("ext4", "-J device=/dev/other", "external"),
            ("ext4", "-z /tmp/undo", "external"),
            ("xfs", "-d name=/dev/other", "external"),
            ("xfs", "-l logdev=/dev/other", "external"),
            ("xfs", "-r rtdev=/dev/other", "external"),
            ("xfs", "-c options=/tmp/config", "external"),
            ("xfs", "-m uuid=generate", "label or UUID"),
            ("xfs", "-m crc=0", "v5"),
        ]
        host_deps = ["is_linux_reinstall_target", "is_fs_args_set", "is_use_cloud_image",
                     "get_install_fs_backend", "verify_xfs_compatibility"]
        for fs, options, message in cases:
            for label, source, shell, verifier in [
                ("host", HOST, ["bash"], "verify_fs_args"),
                *[(label, LIVE, shell, "verify_fs_runtime_config") for label, shell in SHELLS],
            ]:
                with self.subTest(fs=fs, options=options, verifier=label):
                    code = definitions(source, SAFETY_NAMES + [verifier])
                    if source is HOST:
                        code += definitions(HOST, host_deps)
                        code += '\nis_distro_like_debian() { return 1; }\n'
                    code += '\nfs_type=$1; fs_options=$2; fs_type_set=1; distro=ubuntu; cloud_image=1\n'
                    code += verifier
                    self.assert_rejected(self.run_shell(code, [fs, options], shell), message)

    def test_documented_options_still_pass(self):
        cases = [("ext4", "-i 131072"), ("ext4", "-m 0 -E lazy_itable_init=0"),
                 ("ext4", "-O ^metadata_csum_seed,^orphan_file"),
                 ("xfs", "-m reflink=1,rmapbt=0"), ("xfs", "-m crc=1 -l size=32m")]
        for fs, options in cases:
            for label, shell in SHELLS:
                with self.subTest(fs=fs, options=options, shell=label):
                    code = definitions(LIVE, SAFETY_NAMES + ["verify_fs_runtime_config"])
                    code += '\nfs_type=$1; fs_options=$2; verify_fs_runtime_config'
                    self.assert_success(self.run_shell(code, [fs, options], shell))


class FormatterTests(ShellTests):
    def format_image(self, fs, options, folder):
        image = Path(folder) / "root image.img"
        with image.open("wb") as file:
            file.truncate(512 * 1024 * 1024)
        code = definitions(LIVE, SAFETY_NAMES + ["verify_fs_runtime_config",
                                               "get_root_fs_type", "format_root_partition"])
        code += '\nfs_type=$1; fs_options=$2; verify_fs_runtime_config; format_root_partition "$3" os ""'
        self.assert_success(self.run_shell(code, [fs, options, str(image)]))
        result = subprocess.run(["blkid", "-p", "-o", "export", str(image)],
                                text=True, capture_output=True, check=True)
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        self.assertEqual(fields["TYPE"], fs)
        self.assertEqual(fields["LABEL"], "os")
        return image

    @unittest.skipUnless(all(shutil.which(tool) for tool in ["mkfs.ext4", "blkid", "dumpe2fs"]),
                         "requires e2fsprogs and blkid")
    def test_ext4_inode_option_with_real_formatter(self):
        with tempfile.TemporaryDirectory(prefix="fs-raid-format-") as folder:
            image = self.format_image("ext4", "-i 131072", folder)
            result = subprocess.run(["dumpe2fs", "-h", str(image)], text=True, capture_output=True,
                                    check=True, env=dict(os.environ, LC_ALL="C"))
            self.assertEqual(int(re.search(r"Inode count:\s+(\d+)", result.stdout).group(1)), 4096)

    @unittest.skipUnless(all(shutil.which(tool) for tool in ["mkfs.xfs", "blkid", "xfs_db"]),
                         "requires xfsprogs and blkid")
    def test_xfs_metadata_options_with_real_formatter(self):
        with tempfile.TemporaryDirectory(prefix="fs-raid-format-") as folder:
            image = self.format_image("xfs", "-m reflink=1,rmapbt=0", folder)
            result = subprocess.run(["xfs_db", "-r", "-c", "version", str(image)],
                                    text=True, capture_output=True, check=True)
            self.assertIn("REFLINK", result.stdout)
            self.assertNotIn("RMAPBT", result.stdout)


class HelperTests(ShellTests):
    def test_live_updates_validate_before_replacing_script(self):
        self.assertEqual(function(HOST, "verify_trans_script"), function(LIVE, "verify_trans_script"))
        version = re.search(r"(?m)^SCRIPT_VERSION=(.*)$", HOST).group(1)
        protocol = re.search(r"(?m)^FS_RAID_VERSION=(.*)$", HOST).group(1)
        for accepted in [False, True]:
            for label, shell in SHELLS:
                with self.subTest(accepted=accepted, shell=label), tempfile.TemporaryDirectory() as folder:
                    folder = Path(folder)
                    destination = folder / "current.sh"
                    download = folder / "download.sh"
                    destination.write_text("original script\n")
                    download.write_text(LIVE if accepted else f"SCRIPT_VERSION={version}\n")
                    code = definitions(LIVE, ["verify_trans_script", "update_trans_script"]) + '''
wget() { cp "$TASK_DOWNLOAD" "$2"; }
SCRIPT_VERSION=$1; FS_RAID_VERSION=$2; confhome=https://example.invalid
update_trans_script "$3"
'''
                    result = self.run_shell(code, [version, protocol, str(destination)], shell,
                                           {"TASK_DOWNLOAD": str(download)})
                    if accepted:
                        self.assert_success(result)
                        self.assertEqual(destination.read_text(), LIVE)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(destination.read_text(), "original script\n")
                    self.assertEqual(sorted(p.name for p in folder.iterdir()), ["current.sh", "download.sh"])

    def test_helper_protocol_rejects_upstream_and_stale_files(self):
        version = re.search(r"(?m)^SCRIPT_VERSION=(.*)$", HOST).group(1)
        protocol = re.search(r"(?m)^FS_RAID_VERSION=(.*)$", HOST).group(1)
        code = definitions(HOST, ["verify_trans_script"])
        code += '\nSCRIPT_VERSION=$1; FS_RAID_VERSION=$2; verify_trans_script "$3"'
        cases = [
            (f"SCRIPT_VERSION={version}\n", False),
            (f"SCRIPT_VERSION={version}\nFS_RAID_VERSION=1\n", False),
            (f"SCRIPT_VERSION=old\nFS_RAID_VERSION={protocol}\n", False),
            (f"# SCRIPT_VERSION={version}\n# FS_RAID_VERSION={protocol}\n", False),
            (LIVE, True),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trans.sh"
            for content, accepted in cases:
                path.write_text(content)
                result = self.run_shell(code, [version, protocol, str(path)])
                if accepted:
                    self.assert_success(result)
                else:
                    self.assert_rejected(result, "Incompatible trans.sh")

    def test_local_upstream_helper_is_rejected_before_installation(self):
        version = re.search(r"(?m)^SCRIPT_VERSION=(.*)$", HOST).group(1)
        protocol = re.search(r"(?m)^FS_RAID_VERSION=(.*)$", HOST).group(1)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "trans.sh").write_text(f"SCRIPT_VERSION={version}\n")
            code = definitions(HOST, ["copy_or_download_conf_file", "verify_trans_script"])
            code += '''
curl() { printf 'unexpected download\\n' >&2; exit 88; }
SCRIPT_VERSION=$1; FS_RAID_VERSION=$2; THIS_SCRIPT=$3
copy_or_download_conf_file trans.sh "$4"
verify_trans_script "$4"
printf 'installation continued\\n'
'''
            result = self.run_shell(code, [version, protocol, str(folder / "reinstall.sh"),
                                           str(folder / "embedded.sh")])
            self.assert_rejected(result, "Incompatible trans.sh")
            self.assertNotIn("installation continued", result.stdout)

    def test_windows_china_route_matches_fork_mirror(self):
        batch = (ROOT / "reinstall.bat").read_bytes()
        self.assertNotIn(b"\n", batch.replace(b"\r\n", b""))
        windows_url = re.search(r"(?m)^set confhome_cn=(.*)$", batch.decode()).group(1).strip()
        host_url = re.search(r"(?m)^confhome_cn=(.*)$", HOST).group(1).strip()
        self.assertEqual(windows_url, host_url)
        self.assertNotIn("bin456789", windows_url)


CACHE_NAMES = ["is_use_raid", "is_raid_args_set", "is_use_cloud_image",
               "verify_raid_runtime_config", "verify_raid_disk_count",
               "get_raid_disk_identity", "verify_raid_disk_cache", "save_raid_disk_cache",
               "resolve_raid_disks", "get_root_fs_type", "get_raid_level_module",
               "verify_live_raid_modules", "disk_part", "is_ends_with_digit",
               "set_raid_part_arrays", "create_ubuntu_raid_part"]

CACHE_STUBS = '''
get_config() { command cat "$TASK_CONFIG_DIR/$1"; }
set_config() { printf '%s' "$2" >"$TASK_CONFIG_DIR/$1"; }
is_raid_disk_name_whole_disk() { case "$1" in sda | sdb | sdc) return 0 ;; *) return 1 ;; esac; }
cat() {
    case "$1" in
    /sys/block/sda/diskseq) printf '%s\\n' "${TASK_SDA_ID:-100}" ;;
    /sys/block/sdb/diskseq) printf '200\\n' ;;
    /sys/block/sdc/diskseq) printf '300\\n' ;;
    *) command cat "$@" ;;
    esac
}
resolve_raid_disk_selector() {
    if [ "${TASK_LOOKUP_FAIL:-0}" = 1 ]; then exit 89; fi
    case "$1" in aaaaaaaa) printf sda ;; bbbbbbbb) printf sdb ;; *) exit 89 ;; esac
}
apk() { :; }; update_part_raid_disks() { :; }; get_cloud_image_part_size() { printf 700MiB; }
is_efi() { return "${TASK_BIOS:-0}"; }; modprobe() { return "${TASK_MODPROBE_STATUS:-0}"; }
mkdir() { :; }
wipefs() { printf 'wipefs %s\\n' "$*"; }
parted() { printf 'parted %s\\n' "$*"; }
mdadm() { printf 'mdadm %s\\n' "$*"; }
mkfs.ext4() { printf 'mkfs.ext4 %s\\n' "$*"; }
mkfs.fat() { printf 'mkfs.fat %s\\n' "$*"; }
raid_level=1; raid_disks=aaaaaaaa,bbbbbbbb; distro=ubuntu; cloud_image=1; fs_type=ext4
'''


class DiskCacheTests(ShellTests):
    def cached_config(self, folder):
        values = {"raid_disk_names": "sda sdb", "raid_installer_disk": "sda",
                  "raid_disk_selectors": "aaaaaaaa,bbbbbbbb",
                  "raid_disk_identities": "sda:100\nsdb:200\n"}
        for name, value in values.items():
            (Path(folder) / name).write_text(value)

    def run_cached(self, folder, tail, shell, env=None):
        return self.run_shell(definitions(LIVE, CACHE_NAMES) + CACHE_STUBS + tail,
                              shell=shell, env=dict(TASK_CONFIG_DIR=folder, **(env or {})))

    def test_first_resolution_records_disk_identities(self):
        for label, shell in SHELLS:
            with self.subTest(shell=label), tempfile.TemporaryDirectory() as folder:
                self.assert_success(self.run_cached(folder, '\nresolve_raid_disks', shell))
                self.assertEqual((Path(folder) / "raid_disk_selectors").read_text(), "aaaaaaaa,bbbbbbbb")
                self.assertEqual((Path(folder) / "raid_disk_identities").read_text(), "sda:100\nsdb:200\n")
                self.assertEqual((Path(folder) / "raid_disk_names").read_text(), "sda sdb")

    def test_retry_survives_partition_uuid_replacement(self):
        for label, shell in SHELLS:
            with self.subTest(shell=label), tempfile.TemporaryDirectory() as folder:
                self.cached_config(folder)
                result = self.run_cached(folder, '\nresolve_raid_disks; create_ubuntu_raid_part', shell,
                                         {"TASK_LOOKUP_FAIL": "1"})
                self.assert_success(result)
                self.assertIn("wipefs -a -f /dev/sda", result.stdout)

    def test_bad_cache_aborts_before_wiping(self):
        cases = [
            ("changed selectors", '\nraid_disks=virtio-new-a,virtio-new-b', {}, {}, "selectors changed"),
            ("replacement disk", '', {}, {"TASK_SDA_ID": "999"}, "identity changed"),
            ("legacy cache", '', {"raid_disk_selectors": ""}, {}, "selectors changed"),
            ("missing identities", '', {"raid_disk_identities": ""}, {}, "identity changed"),
            ("missing member", '', {"raid_disk_names": "sda missing"}, {}, "missing"),
            ("duplicate members", '', {"raid_disk_names": "sda sda"}, {}, "Duplicate"),
            ("installer outside array", '', {"raid_installer_disk": "sdc"}, {}, "not an array member"),
            ("too few members", '', {"raid_disk_names": "sda"}, {}, "at least 2"),
            ("live kernel unsupported", '', {}, {"TASK_MODPROBE_STATUS": "1"}, "live kernel cannot load"),
        ]
        for name, tail, changes, env, message in cases:
            for label, shell in SHELLS:
                with self.subTest(case=name, shell=label), tempfile.TemporaryDirectory() as folder:
                    self.cached_config(folder)
                    for key, value in changes.items():
                        (Path(folder) / key).write_text(value)
                    result = self.run_cached(folder, tail + '\nresolve_raid_disks; create_ubuntu_raid_part', shell, env)
                    self.assert_rejected(result, message)
                    self.assertNotIn("wipefs", result.stdout)
                    self.assertNotIn("parted", result.stdout)

    def test_boot_format_and_partition_layout_for_bios_and_efi(self):
        for bios in ["0", "1"]:
            for label, shell in SHELLS:
                with self.subTest(bios=bios, shell=label), tempfile.TemporaryDirectory() as folder:
                    self.cached_config(folder)
                    result = self.run_cached(folder, '\nresolve_raid_disks; create_ubuntu_raid_part', shell,
                                             {"TASK_BIOS": bios})
                    self.assert_success(result)
                    self.assertIn("mkfs.ext4 -F -O ^metadata_csum_seed,^orphan_file -L boot /dev/md/boot", result.stdout)
                    self.assertIn("mkpart", result.stdout)
                    self.assertIn("set 1 " + ("bios_grub" if bios == "1" else "esp") + " on", result.stdout)


class ResyncTests(ShellTests):
    def test_resync_wait_and_completion_races(self):
        cases = [("resync", "idle", "0", True), ("resync", "idle", "1", True),
                 ("recover", "idle", "0", True), ("idle", "idle", "1", True),
                 ("frozen", "frozen", "1", True), ("resync", "resync", "1", False),
                 ("unknown", "unknown", "0", False)]
        for action, after, status, succeeds in cases:
            for label, shell in SHELLS:
                with self.subTest(action=action, status=status, shell=label), tempfile.TemporaryDirectory() as folder:
                    path = Path(folder) / "action"
                    path.write_text(action)
                    code = definitions(LIVE, ["wait_for_raid_resync"]) + '''
readlink() { printf /dev/md-test; }
cat() { command cat "$TASK_ACTION_FILE"; }
mdadm() { printf '%s' "$TASK_ACTION_AFTER" >"$TASK_ACTION_FILE"; return "$TASK_WAIT_STATUS"; }
wait_for_raid_resync /dev/md/root
'''
                    result = self.run_shell(code, shell=shell, env={"TASK_ACTION_FILE": str(path),
                                             "TASK_ACTION_AFTER": after, "TASK_WAIT_STATUS": status})
                    if succeeds:
                        self.assert_success(result)
                    else:
                        self.assertEqual(result.returncode, 97, result.stderr)

    def test_growth_waits_and_skips_non_growing_levels(self):
        for level in ["0", "linear", "1", "5"]:
            for label, shell in SHELLS:
                with self.subTest(level=level, shell=label):
                    code = definitions(LIVE, ["is_raid_root_size_grow_supported", "resize_after_install_raid_cloud_image"])
                    code += '''
apk() { :; }; verify_raid_disk_cache() { :; }; stop_md_arrays() { :; }; parted() { :; }
update_part_raid_disks() { :; }; refresh_raid_arrays() { :; }
wait_for_raid_resync() { task_waited=1; printf 'waited\\n'; }
mdadm() { [ "$task_waited" = 1 ] || exit 88; printf 'grown\\n'; }
e2fsck() { return 1; }; resize2fs() { printf 'filesystem resized\\n'; }
raid_level=$1; raid_disk_names='sda sdb'; target_os_fstype=ext4
resize_after_install_raid_cloud_image
'''
                    result = self.run_shell(code, [level], shell)
                    self.assert_success(result)
                    if level in ["1", "5"]:
                        self.assertEqual(result.stdout, "waited\ngrown\nfilesystem resized\n")
                    else:
                        self.assertNotIn("grown", result.stdout)


class KernelTests(ShellTests):
    def test_linear_kernel_choice_preserves_other_raid_flavors(self):
        code = definitions(LIVE, ["is_use_raid", "is_ubuntu_lts", "get_ubuntu_kernel_flavor"]) + '''
is_virt() { return "$TASK_IS_PHYSICAL"; }; is_virt_contains() { return 1; }
cache_dmi_and_virt() { :; }; get_cloud_vendor() { printf aws; }
releasever=$1; raid_level=$2; raid_disks=a,b; TASK_IS_PHYSICAL=$3
get_ubuntu_kernel_flavor
'''
        cases = [("22.04", "linear", "0", "virtual"),
                 ("24.04", "linear", "0", "virtual-hwe-24.04"),
                 ("26.04", "linear", "1", "generic-hwe-26.04"),
                 ("22.04", "1", "0", "aws"), ("24.04", "5", "0", "aws")]
        for version, level, physical, expected in cases:
            for label, shell in SHELLS:
                with self.subTest(version=version, level=level, shell=label):
                    result = self.run_shell(code, [version, level, physical], shell)
                    self.assert_success(result)
                    self.assertEqual(result.stdout.strip(), expected)

    def test_installed_kernel_modules_and_missing_extras(self):
        for mode in ["available", "extra", "unsupported", "missing", "no-kernel"]:
            for label, shell in SHELLS:
                with self.subTest(mode=mode, shell=label), tempfile.TemporaryDirectory() as folder:
                    folder = Path(folder)
                    (folder / "boot").mkdir()
                    if mode != "no-kernel":
                        (folder / "boot/vmlinuz-6.8-test").touch()
                    if mode == "unsupported":
                        (folder / "boot/config-6.8-test").write_text("CONFIG_MD_RAID1=m\n")
                    code = definitions(LIVE, ["get_raid_level_module", "get_root_fs_type", "ensure_ubuntu_raid_kernel_modules"])
                    code += '''
chroot() {
    [ "$2 $3 $4 $5 $6" = 'modprobe --set-version 6.8-test --show-depends --ignore-install' ] || exit 88
    if [ "$TASK_MODE" = available ] || { [ "$TASK_MODE" = extra ] && [ "$task_extra" = 1 ]; }; then return 0; fi
    [ "${7}" != linear ]
}
chroot_apt_install() { task_extra=1; printf 'extras %s\\n' "$2"; }
raid_level=linear; target_os_fstype=ext4
ensure_ubuntu_raid_kernel_modules "$1"
'''
                    result = self.run_shell(code, [str(folder)], shell, {"TASK_MODE": mode})
                    if mode in ["available", "extra"]:
                        self.assert_success(result)
                        self.assertEqual("extras linux-modules-extra-6.8-test" in result.stdout, mode == "extra")
                    elif mode == "unsupported":
                        self.assert_rejected(result, "does not support linear")
                    elif mode == "missing":
                        self.assert_rejected(result, "missing linear")
                    else:
                        self.assert_rejected(result, "Could not find an installed Ubuntu kernel")


if __name__ == "__main__":
    unittest.main()
