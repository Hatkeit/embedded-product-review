# Lipeat iOS 앱 (Capacitor)

`../lipeat` 웹 앱을 그대로 감싼 iPhone 앱 프로젝트입니다. Mac과 Xcode, 무료 Apple ID만 있으면 본인 iPhone에 설치할 수 있습니다. 코드를 고칠 필요는 없고 아래 순서대로 따라 하면 됩니다.

## 0. 준비물

- Apple Silicon 또는 Intel Mac (M1 MacBook Air 가능)
- Xcode: Mac App Store에서 **Xcode** 검색 → 받기 (용량이 커서 30분 이상 걸릴 수 있음). 설치 후 한 번 실행해서 추가 구성 요소 설치에 동의합니다.
- Node.js: https://nodejs.org 에서 LTS 버전을 받아 설치합니다.
- iPhone과 케이블, 그리고 App Store에 로그인된 Apple ID

## 1. 코드 받기와 준비 (터미널)

Mac에서 **터미널** 앱을 열고 한 줄씩 붙여넣어 실행합니다.

```bash
# 리포지토리 받기 (이미 받았다면 건너뜀)
git clone https://github.com/Hatkeit/embedded-product-review.git
cd embedded-product-review
git checkout claude/lipeat-app-info-of8kvj   # main에 합쳐졌다면 이 줄은 생략

# iOS 프로젝트 폴더로 이동해 도구 설치
cd lipeat-ios
npm install

# 웹 앱 파일을 iOS 프로젝트로 복사하고 Xcode 열기
npx cap sync ios
npx cap open ios
```

마지막 명령으로 Xcode가 열립니다. (열리지 않으면 Finder에서 `lipeat-ios/ios/App/App.xcodeproj`를 더블클릭합니다.) 처음 열면 Xcode가 Capacitor 패키지를 자동으로 내려받으니 1~2분 기다립니다.

## 2. Xcode에서 서명 설정 (한 번만)

1. 메뉴 **Xcode → Settings… → Accounts** 탭 → 왼쪽 아래 **+** → **Apple ID** → App Store에 쓰는 Apple ID로 로그인합니다.
2. 왼쪽 파일 목록 맨 위의 파란 **App** 아이콘을 클릭 → 가운데 **TARGETS → App** 선택 → 상단 **Signing & Capabilities** 탭.
3. **Automatically manage signing** 체크 → **Team**에서 방금 로그인한 계정 `(Personal Team)` 선택.
4. **Bundle Identifier**를 본인만의 값으로 바꿉니다. 예: `com.홍길동.lipeat` (영문 소문자만, 다른 사람과 겹치지 않으면 됩니다). 빨간 오류가 사라지면 완료입니다.

## 3. iPhone에 설치

1. iPhone을 케이블로 Mac에 연결하고, iPhone에서 "이 컴퓨터를 신뢰하겠습니까?"에 **신뢰**를 누릅니다.
2. iPhone **설정 → 개인정보 보호 및 보안 → 개발자 모드**를 켜고 재시동합니다. (iOS 16 이상. 이 메뉴는 Xcode에 한 번 연결된 뒤에 나타납니다.)
3. Xcode 상단 가운데 기기 선택 칸에서 본인 iPhone을 고릅니다.
4. 왼쪽 위 **▶ (Run)** 버튼을 누릅니다. 빌드가 끝나면 앱이 iPhone에 설치되고 실행됩니다.
5. 처음 실행 시 "신뢰하지 않는 개발자" 메시지가 뜨면 iPhone **설정 → 일반 → VPN 및 기기 관리** → 본인 Apple ID → **신뢰**를 누른 뒤 앱을 다시 엽니다.

## 4. 이후에 할 일

- **7일마다 재설치**: 무료 Apple ID로 설치한 앱은 7일 뒤 실행되지 않습니다. iPhone을 연결하고 Xcode에서 ▶를 다시 누르면 됩니다. 앱 안의 학습 데이터는 그대로 유지됩니다. 연 99달러 개발자 계정으로 바꾸면 1년 동안 유지됩니다.
- **웹 앱을 수정했을 때**: `lipeat/index.html`을 고친 뒤 터미널에서 `cd lipeat-ios && npx cap sync ios`를 실행하고 Xcode에서 ▶를 누르면 반영됩니다.
- **케이블 없이 실행**: Xcode 메뉴 **Window → Devices and Simulators**에서 iPhone을 선택하고 **Connect via network**를 켜면 같은 Wi-Fi에서 무선으로 설치할 수 있습니다.

## 자주 나오는 오류

| 메시지 | 해결 |
| --- | --- |
| `Signing for "App" requires a development team` | 2단계에서 Team을 선택하지 않았습니다. |
| `Failed to register bundle identifier` | Bundle Identifier가 이미 쓰이는 값입니다. 다른 이름으로 바꿉니다. |
| `Untrusted Developer` / 신뢰하지 않는 개발자 | 3-5단계대로 iPhone 설정에서 신뢰합니다. |
| `Could not launch "App"` 개발자 모드 관련 | 3-2단계 개발자 모드를 켭니다. |
| `xcrun: error` / `command line tools` | Xcode를 한 번 실행하고, **Xcode → Settings → Locations → Command Line Tools**에서 Xcode 버전을 선택합니다. |
| 패키지 해석 실패(네트워크) | Xcode 메뉴 **File → Packages → Reset Package Caches** 후 다시 시도합니다. |

## 앱 안에서

- 「로컬 파일」로 사진 앱이나 파일 앱의 영상을 고를 수 있습니다.
- 「자막 만들기」(브라우저 내 Whisper)는 iPhone 메모리 한계로 tiny 모델과 10분 이내 영상을 권장합니다. 모델은 처음 한 번만 내려받습니다.
- 마이크 권한은 녹음 모드를 처음 쓸 때 묻습니다.
- 학습 데이터는 앱 안에 저장됩니다. 앱을 삭제하면 사라지므로 라이브러리의 「백업 내보내기」로 보관하세요.
