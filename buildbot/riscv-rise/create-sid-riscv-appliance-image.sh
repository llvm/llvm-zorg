#!/bin/sh
#===----------------------------------------------------------------------===//
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//

TGT=riscv-sid-for-qemu
# Uses <https://github.com/muxup/medley/blob/main/rootless-debootstrap-wrapper>
~/rootless-debootstrap-wrapper \
  --arch=riscv64 \
  --suite=sid \
  --cache-dir="$HOME/debcache" \
  --target-dir=$TGT \
  --include=linux-image-riscv64,zstd,dbus,adduser,python3,python3-psutil,git
cat - <<EOF > $TGT/etc/resolv.conf
nameserver 1.1.1.1
EOF
"$TGT/_enter" sh -e <<'EOF'
ln -sf /dev/null /etc/udev/rules.d/80-net-setup-link.rules # disable persistent network names
cat - <<INNER_EOF > /etc/systemd/network/10-eth0.network
[Match]
Name=eth0

[Network]
DHCP=yes
INNER_EOF
systemctl enable systemd-networkd
echo root:root | chpasswd
adduser --gecos ",,," --disabled-password user
echo user:user | chpasswd
ln -sf /dev/null /etc/systemd/system/serial-getty@hvc0.service
ln -sf /dev/null /etc/systemd/system/serial-getty@ttyS0.service

cat - <<'INNER_EOF' > /opt/on-boot-logic.sh
#!/bin/sh
error() {
  printf "!!!!!!!!!! Error: %s !!!!!!!!!!\n" "$*" >&2
  exit 1
}

mkdir -p /mnt/hgcomm
mount -t 9p -o trans=virtio,version=9p2000.L hgcomm /mnt/hgcomm || error "Failed to mount hgcomm"
if [ -e /mnt/hgcomm/debug-mode-on ]; then
  echo "debug-mode-on file present: Not executing exec-on-boot and instead starting getty"
  systemctl unmask serial-getty@ttyS0.service
  systemctl start serial-getty@ttyS0.service
  systemctl mask serial-getty@ttyS0.service
  exit 0
fi
[ -f /mnt/hgcomm/exec-on-boot ] || error "exec-on-boot doesn't exist"
[ -x /mnt/hgcomm/exec-on-boot ] || error "exec-on-boot isn't executable"
/mnt/hgcomm/exec-on-boot
echo "$?" > /mnt/hgcomm/exec-on-boot.exitcode
poweroff
INNER_EOF
chmod +x /opt/on-boot-logic.sh

cat - <<'INNER_EOF' > /etc/systemd/system/appliance.service
[Unit]
Description=Execute on boot logic
After=multi-user.target

[Service]
Type=oneshot
StandardOutput=tty
TTYPath=/dev/ttyS0
ExecStart=/opt/on-boot-logic.sh
ExecStopPost=/bin/sh -c '[ "$EXIT_STATUS" != 0 ] && poweroff'

[Install]
WantedBy=multi-user.target
INNER_EOF
systemctl enable appliance.service
echo "Finished rootfs config"
EOF

fakeroot -i $TGT/.fakeroot.env sh <<EOF
ln -L $TGT/vmlinuz kernel
ln -L $TGT/initrd.img initrd
fallocate -l 30GiB rootfs.img
mkfs.ext4 -d $TGT rootfs.img
EOF
