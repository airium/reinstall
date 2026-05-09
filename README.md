<!-- markdownlint-disable MD028 MD033 MD045 -->

[**English Version**](README.en.md)

---

### 修改版 reinstall 脚本

请参见原始仓库 <https://github.com/bin456789/reinstall> 了解使用说明

---

#### 指定文件系统和格式化参数

`--fs-type ...` 指定根分区文件系统。目前可用值为 `default|ext4|xfs`，默认值为 `default` 即保持发行版默认逻辑。xfs 要求 XFS v5 格式，对应需要最低 Linux 5.10 内核，因此仅支持较新的发行版。

`--fs-options ...` 追加到 mkfs 的参数，仅作用于根分区，且必须和 `--fs-type ext4|xfs` 一起使用。仅支持由 `trans.sh` 直接对根分区执行 mkfs 的安装方案，采用不支持的安装方案时会报错。

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/support-fs-opt/reinstall.sh || wget -O ${_##*/} $_

# 使用 xfs 文件系统安装 Debian 13
bash reinstall.sh debian 13 --fs-type xfs
# 使用 ext4 文件系统和 128KB inode size 安装 Ubuntu 24.04
bash reinstall.sh ubuntu 24.04 --fs-type ext4 --fs-options '-i 131072'
# 使用 xfs 文件系统并关闭 reflink 和 rmapbt 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --fs-type xfs --fs-options '-m reflink=0,rmapbt=0'
```

> [!NOTE]
> 目前仅支持 EXT4 和 XFS
>
> XFS 仅支持 Debian 11+、Ubuntu 22.04+、Anolis 8+、OpenCloudOS 9+、openEuler 22.03+、Oracle 云镜像模板，以及使用 mkfs 的滚动发行版
>
> 仅支持国外服务器安装, 因为没有部署国内脚本镜像站点

---

#### 使用 MDADM 安装文件系统

`--raid-level ...` 指定 RAID 级别。目前可用值为 `linear|0|1|5`。

`--raid-disks ...` 指定哪些硬盘参与组建 RAID, 使用 `,` 分开。

```bash
curl -O https://raw.githubusercontent.com/airium/reinstall/add-raid/reinstall.sh || wget -O ${_##*/} $_

# 以设备路径方式指定两块盘组建 RAID 0 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 0 --raid-disks /dev/sda,/dev/sdb
# 以 ID 方式指定两块盘组建 RAID Linear 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level linear --raid-disks 'virtio-5ee85skf9mo1e8c2d64l,virtio-2r1yvcr1g6tybooi9lm0'
# 以 UUID 方式指定三块盘组建 RAID 5 安装 Ubuntu 26.04
bash reinstall.sh ubuntu 26.04 --raid-level 5 --raid-disks 'f2da2da2-3f55-4c46-a329-2e1f32528395,6095df47-96dc-434a-b400-18db8696f7e9,4689bcae-3ad4-4e5a-9363-2c38455c51e9'
```

> [!NOTE]
> 目前仅支持 Ubuntu
>
> 仅支持国外服务器安装, 因为没有部署国内脚本镜像站点
