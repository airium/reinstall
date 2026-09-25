<!-- markdownlint-disable MD028 MD033 MD045 -->

[**English Version**](README.en.md)

---

### 修改版 reinstall 脚本

请参见原始仓库 <https://github.com/bin456789/reinstall> 了解使用说明

修改版源码：<https://github.com/airium/reinstall>

---

#### 指定文件系统和格式化参数

`--fs-type ...` 指定根分区文件系统。目前可用值为 `default|ext4|xfs`，默认值为 `default` 即保持发行版默认逻辑。xfs 要求 XFS v5 格式，对应需要最低 Linux 5.10 内核，因此仅支持较新的发行版。

`--fs-options ...` 追加到 mkfs 的参数，仅作用于根分区，且必须和 `--fs-type ext4|xfs` 一起使用。仅支持由 `trans.sh` 直接对根分区执行 mkfs 的安装方案，采用不支持的安装方案时会报错。

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/main/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# 使用 xfs 文件系统安装 Debian 13
bash reinstall.sh debian 13 --fs-type xfs
# 使用 ext4 文件系统和每 128KB 一个 inode 安装 Ubuntu 24.04
bash reinstall.sh ubuntu 24.04 --fs-type ext4 --fs-options '-i 131072' --username root
# 使用 xfs 文件系统并关闭 reflink 和 rmapbt 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --fs-type xfs --fs-options '-m reflink=1,rmapbt=0' --username root
```

> [!NOTE]
> 目前仅支持 EXT4 和 XFS
>
> `--fs-options` 不能设置文件系统 label、UUID，或覆盖文件系统类型（例如 EXT4 的 `-t` 参数）；这些值由脚本控制，以保证 bootloader 和 fstab 配置一致。
>
> 会禁用元数据 CRC 的 XFS 参数（例如 `-m crc=0`）会被拒绝，因为它会创建旧版 XFS v4 文件系统。
>
> XFS 仅支持脚本放行的安装路径：Debian 11+ 和 Kali 安装器安装；Ubuntu 22.04+ 云镜像或安装器安装；Anolis 8+、OpenCloudOS 9+、openEuler 22.03+、CentOS Stream 9/10、Red Hat 和 Oracle 云镜像模板、AlmaLinux/Rocky 9+；以及直接 mkfs 的 Alpine、Arch、Gentoo、AOSC 和 NixOS。Fedora/openSUSE 等直接写盘镜像路径以及 fnOS/FygoOS 不支持 XFS。

---

#### 使用 MDADM 安装文件系统

`--raid-level ...` 指定根分区 RAID 级别。目前可用值为 `linear|0|1|5`。

`--raid-disks ...` 指定哪些整盘硬盘参与组建 RAID，使用 `,` 分开。可使用 `/dev/...` 设备路径、磁盘 PTUUID、`/dev/disk/by-id/...` 路径或 by-id 名称。PTUUID 必须在所有已连接磁盘中唯一；有歧义的 PTUUID 会在格式化前被拒绝，克隆磁盘应改用 by-id 选择器。目前可直接传入 initrd 的 by-id 名称仅限 `ata-*`、`mmc-*`、`nvme-*`、`virtio-*`、`wwn-0x*`。`/dev/...` 和其他 by-id 路径只能在 Linux 下运行脚本时预先转换；从 Windows 启动安装时请使用磁盘 PTUUID 或上述稳定 by-id 选择器。

根分区使用指定 RAID 级别，`/boot` 固定使用 MDADM RAID1，EFI 或 BIOS 引导分区会写入每块成员盘。

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/main/reinstall.sh || wget -O ${_##*/} $_
```

```bash
# 以稳定 by-id 名称指定两块盘组建 RAID 1 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 1 --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# 以稳定 by-id 名称指定两块盘组建 RAID 0 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 0 --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# 以稳定 by-id 名称指定两块盘组建 linear RAID 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level linear --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# 以 PTUUID 方式指定三块盘组建 RAID 5 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 5 --raid-disks 'f2da2da2-3f55-4c46-a329-2e1f32528395,6095df47-96dc-434a-b400-18db8696f7e9,4689bcae-3ad4-4e5a-9363-2c38455c51e9'
```

> [!NOTE]
> 目前仅支持 Ubuntu 云镜像安装。RAID 不支持 `--installer`，也不能和 `--target-disk` 同时使用
>
> RAID 0 和 linear 的 Safe v1 支持不会把原本预留给临时 installer 的空间加入根阵列/根文件系统。
