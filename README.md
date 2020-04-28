# blocksync

This repo is inspired by https://github.com/theraser/blocksync

# Roadmap

## Local

- [x] LocalSyncer 구현
- [x] Event handler 추가
- [ ] dryrun 기능 추가
- [ ] Multiprocessing or Concurrency(async, threading) 지원
  - Worker(Process)별로 작업량과 범위 할당

## Remote

- [ ] RemoteSyncer 구조 설계
- [ ] Event handler 추가
- [ ] Multiprocessing 지원
  - Worker(Process)별로 작업량과 범위 할당
- [ ] Remote-Remote 동기화 기능 지원
- [ ] 1-N 동기화 기능 추가
  - 직렬 동기화(Sequence)
  - 병렬 동기화(Concurrency)
- [ ] Compression 지원
- [ ] SSH cipher 지원
- [ ] hashing, double hashing 지원
- [ ] dryrun 기능 추가
