"""Install verified official SDK archives and Gradle into repo-local ignored .tools."""
import hashlib, pathlib, urllib.request, xml.etree.ElementTree as ET, zipfile, platform
root=pathlib.Path(__file__).resolve().parents[1]; out=root/'.tools'; sdk=out/'android-sdk'; sdk.mkdir(parents=True,exist_ok=True)
if not (out/'repository.xml').exists(): urllib.request.urlretrieve('https://dl.google.com/android/repository/repository2-3.xml',out/'repository.xml')
repo=ET.parse(out/'repository.xml').getroot()
host='macosx' if platform.system()=='Darwin' else 'linux'
if platform.system() not in ['Darwin','Linux']: raise SystemExit('Use Android Studio SDK Manager on Windows; this helper supports macOS/Linux.')
for path in ['cmdline-tools;latest','platform-tools','platforms;android-35','build-tools;35.0.0']:
 p=next(p for p in repo.findall('remotePackage') if p.attrib['path']==path)
 archives=[a for a in p.findall('./archives/archive') if a.findtext('host-os') in [host,None]]
 architecture='arm64' if platform.machine() in ['arm64','aarch64'] else 'x86_64'
 a=next((a for a in archives if architecture in a.findtext('./complete/url')),archives[0]); name=a.findtext('./complete/url'); f=out/name
 if not f.exists():
  print('Download',name,flush=True); urllib.request.urlretrieve('https://dl.google.com/android/repository/'+name,f)
 assert hashlib.sha1(f.read_bytes()).hexdigest()==a.findtext('./complete/checksum')
 if path=='cmdline-tools;latest':
  dest=out/'cmdline-unpack'; dest.mkdir(exist_ok=True); zipfile.ZipFile(f).extractall(dest)
  import shutil
  target=sdk/'cmdline-tools/latest'
  if not target.exists(): shutil.copytree(dest/'cmdline-tools',target)
 else:
  zipfile.ZipFile(f).extractall(sdk)
  if path.startswith('platforms;'):
   extracted=sdk/'android-35'; target=sdk/'platforms/android-35'; target.parent.mkdir(exist_ok=True)
   if extracted.exists() and not target.exists(): extracted.rename(target)
  if path.startswith('build-tools;'):
   extracted=sdk/'android-15'; target=sdk/'build-tools/35.0.0'; target.parent.mkdir(exist_ok=True)
   if extracted.exists() and not target.exists(): extracted.rename(target)
for p in sdk.rglob('*'):
 if p.is_file() and (p.parent.name in ['bin','platform-tools','35.0.0'] or p.suffix in ['.sh']): p.chmod(0o755)
f=out/'gradle-8.11.1-bin.zip'
if not f.exists():
 print('Download Gradle',flush=True); urllib.request.urlretrieve('https://downloads.gradle.org/distributions/gradle-8.11.1-bin.zip',f)
expected=urllib.request.urlopen('https://downloads.gradle.org/distributions/gradle-8.11.1-bin.zip.sha256',timeout=30).read().decode().strip()
assert hashlib.sha256(f.read_bytes()).hexdigest()==expected
zipfile.ZipFile(f).extractall(out); (out/'gradle-8.11.1/bin/gradle').chmod(0o755)
(root/'android/local.properties').write_text('sdk.dir='+str(sdk)+'\n')
print('SDK and Gradle ready',flush=True)
