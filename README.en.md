<!-- markdownlint-disable MD028 MD033 MD045 -->

[**中文版**](README.md)

---

### Modified reinstall Script

See the original repository <https://github.com/bin456789/reinstall> for usage instructions.

Modified source: <https://github.com/airium/reinstall>

---

#### Specifying Filesystem Type and Formatting Options

`--fs-type ...` specifies the root partition filesystem. Available values are `default|ext4|xfs`, with `default` as the default value, which preserves the distribution's default logic. XFS requires XFS v5 format, which in turn requires a minimum Linux 5.10 kernel, so it is only supported on newer distributions.

`--fs-options ...` appends arguments to mkfs, applying only to the root partition, and must be used together with `--fs-type ext4|xfs`. It is only supported for installation methods where `trans.sh` directly runs mkfs on the root partition; using an unsupported installation method will result in an error.

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/main/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# Install Debian 13 using XFS filesystem
bash reinstall.sh debian 13 --fs-type xfs
# Install Ubuntu 24.04 using EXT4 filesystem with one inode per 128KB
bash reinstall.sh ubuntu 24.04 --fs-type ext4 --fs-options '-i 131072' --username root
# Install Ubuntu 26.04 using XFS filesystem with reflink and rmapbt disabled
bash reinstall.sh ubuntu 26.04 --fs-type xfs --fs-options '-m reflink=1,rmapbt=0' --username root
```

> [!NOTE]
> Currently only EXT4 and XFS are supported.
>
> `--fs-options` must not set the filesystem label or UUID, or override the filesystem type (for example, with the EXT4 `-t` option); the script controls those values so bootloader and fstab entries remain consistent.
>
> XFS options that disable metadata CRC, such as `-m crc=0`, are rejected because they create legacy XFS v4 filesystems.
>
> XFS is only supported on install paths accepted by the script: Debian 11+ and Kali installer installs; Ubuntu 22.04+ cloud-image or installer installs; Anolis 8+, OpenCloudOS 9+, openEuler 22.03+, CentOS Stream 9/10, Red Hat and Oracle cloud image templates, and AlmaLinux/Rocky 9+; plus mkfs-backed Alpine, Arch, Gentoo, AOSC, and NixOS installs. Image-based dd paths such as Fedora/openSUSE, and fnOS/FygoOS, are not supported.

---

#### Installing with MDADM RAID

`--raid-level ...` specifies the root partition RAID level. Available values are `linear|0|1|5`.

`--raid-disks ...` specifies which whole disks participate in the RAID array, separated by `,`. Accepted selectors are `/dev/...` disk paths, disk PTUUIDs, `/dev/disk/by-id/...` paths, or by-id basenames. PTUUIDs must be unique across all attached disks; ambiguous PTUUIDs are rejected before formatting, so cloned disks should use by-id selectors. Currently, by-id names passed directly into the initrd are limited to `ata-*`, `mmc-*`, `nvme-*`, `virtio-*`, and `wwn-0x*`. `/dev/...` selectors and other by-id paths can only be normalized when running from Linux; when launching from Windows, use disk PTUUIDs or one of those stable by-id selectors.

The root filesystem uses the requested RAID level. `/boot` always uses MDADM RAID1, and EFI or BIOS boot partitions are written to every member disk.

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/main/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# Specify two disks by stable by-id names to build RAID 1 and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 1 --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# Specify two disks by stable by-id names to build RAID 0 and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 0 --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# Specify two disks by stable by-id names to build linear RAID and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level linear --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# Specify three disks by PTUUID to build RAID 5 and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 5 --raid-disks 'f2da2da2-3f55-4c46-a329-2e1f32528395,6095df47-96dc-434a-b400-18db8696f7e9,4689bcae-3ad4-4e5a-9363-2c38455c51e9'
```

> [!NOTE]
> Currently only Ubuntu cloud-image installs are supported. `--installer` and `--target-disk` are not supported with RAID.
>
> For RAID 0 and linear, Safe v1 support does not add the space formerly reserved for the temporary installer to the root array/filesystem.
