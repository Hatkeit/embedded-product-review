#!/bin/bash
cd "$(dirname "$0")"
R=https://mirror.gcr.io/v2/kicad/kicad
ACC="application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"
curl -s -H "Accept: $ACC" "$R/manifests/10.0.6-amd64" > manifest.json
python3 -c "import json; m=json.load(open('manifest.json')); [print(l['digest'], l['size']) for l in m['layers']]; print(m['config']['digest'], 0, file=open('config.txt','w'))" > layers.txt
cat layers.txt
rm -rf rootfs; mkdir -p rootfs
while read DG SZ; do
  echo "layer $DG ($SZ)"
  for i in 1 2 3 4 5; do
    curl -s -L "$R/blobs/$DG" -o layer.tgz
    [ "$(stat -c %s layer.tgz)" = "$SZ" ] && break
    echo "  retry $i (got $(stat -c %s layer.tgz))"; sleep $((2**i))
  done
  tar -xzf layer.tgz -C rootfs --no-same-owner --exclude='dev/*' 2>>tar.err || echo "  tar rc=$?"
  rm -f layer.tgz
done < layers.txt
DG=$(cut -d' ' -f1 config.txt); curl -s -L "$R/blobs/$DG" -o config.json
echo PULL_DONE
