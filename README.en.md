<!-- markdownlint-disable MD028 MD033 MD045 -->

[**中文版**](README.md)

---

### Modified reinstall Script

See the original repository <https://github.com/bin456789/reinstall> for usage instructions.

---

#### Specifying Filesystem Type and Formatting Options

`--fs-type ...` specifies the root partition filesystem. Available values are `default|ext4|xfs`, with `default` as the default value, which preserves the distribution's default logic. XFS requires XFS v5 format, which in turn requires a minimum Linux 5.10 kernel, so it is only supported on newer distributions.

`--fs-options ...` appends arguments to mkfs, applying only to the root partition, and must be used together with `--fs-type ext4|xfs`. It is only supported for installation methods where `trans.sh` directly runs mkfs on the root partition; using an unsupported installation method will result in an error.

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/support-fs-opt/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# Install Debian 13 using XFS filesystem
bash reinstall.sh debian 13 --fs-type xfs
# Install Ubuntu 24.04 using EXT4 filesystem with 128KB inode size
bash reinstall.sh ubuntu 24.04 --fs-type ext4 --fs-options '-i 131072'
# Install Ubuntu 26.04 using XFS filesystem with reflink and rmapbt disabled
bash reinstall.sh ubuntu 26.04 --fs-type xfs --fs-options '-m reflink=1,rmapbt=0'
```

> [!NOTE]
> Currently only EXT4 and XFS are supported.
>
> XFS is only supported on Debian 11+, Ubuntu 22.04+, Anolis 8+, OpenCloudOS 9+, openEuler 22.03+, Oracle Cloud image templates, and rolling-release distributions that use mkfs.
>
> Installation is only supported on servers outside China, as no domestic script mirror sites have been deployed.

---

#### Installing with MDADM RAID

`--raid-level ...` specifies the RAID level. Available values are `linear|0|1|5`.

`--raid-disks ...` specifies which disks participate in the RAID array, separated by `,`.

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/add-raid/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# Specify two disks by device path to build RAID 0 and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 0 --raid-disks /dev/sda,/dev/sdb
# Specify two disks by ID to build RAID Linear and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level linear --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# Specify three disks by UUID to build RAID 5 and install Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 5 --raid-disks 'f2da2da2-3f55-4c46-a329-2e1f32528395,6095df47-96dc-434a-b400-18db8696f7e9,4689bcae-3ad4-4e5a-9363-2c38455c51e9'
```

> [!NOTE]
> Currently only Ubuntu is supported.
>
> Installation is only supported on servers outside China, as no domestic script mirror sites have been deployed.
