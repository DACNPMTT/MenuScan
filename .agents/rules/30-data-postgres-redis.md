# Data Rules — PostgreSQL and Redis

## PostgreSQL là nguồn sự thật

- PostgreSQL 16 lưu dữ liệu bền vững; Redis chỉ là cache/coordination và không
  được là nguồn duy nhất cho user, session, scan, menu hoặc kết quả OCR.
- Schema MVP theo `doc/content/specification/database.md`. Không phát triển dựa
  trên `DB/schema.sql` cũ nếu nó mâu thuẫn specification.
- Table/column dùng `snake_case`, table số nhiều; PK UUID; timestamp `TIMESTAMPTZ`
  UTC; tiền `NUMERIC(14,2)`; metadata linh hoạt mới dùng `JSONB`. Constraint/index
  dùng prefix `pk_`, `fk_`, `uq_`, `ck_`, `ix_`; SQL thuần parameterized, ghi rõ
  column và không dùng `SELECT *`.
- Constraint quan trọng phải có ở DB bên cạnh validation ứng dụng. Chỉ thêm index
  dựa trên query/constraint thực tế.
- Mọi schema change đi qua migration có forward path rõ ràng; không sửa production
  data bằng startup code. Migration phá hủy hoặc không backward compatible cần
  kế hoạch rollout và xác nhận rõ.
- Migration revision/filename mô tả hành động + entity và có rollback, hoặc ghi
  rõ lý do irreversible.
- Chỉ lưu object key và metadata file trong DB; binary thuộc object storage.

## Redis là cache có thể mất

- Redis hiện chưa có service/dependency trong repository. Task dùng Redis phải
  bổ sung dependency, `REDIS_URL`, Compose/config, readiness và test; không
  hard-code connection string.
- Key lowercase có namespace/version/owner scope, ví dụ
  `menuscan:v1:<module>:<scope>:<id>`. TTL constant phải ghi đơn vị. Dữ liệu cache
  phải có TTL; tránh key không hết hạn trừ primitive coordination được mô tả rõ.
- Cache-aside mặc định: đọc cache, miss thì đọc PostgreSQL, ghi với TTL. Mutation
  DB thành công phải invalidate/update cache; ưu tiên invalidation khi consistency
  quan trọng.
- Redis failure phải degrade an toàn về PostgreSQL nếu feature cho phép. Không để
  lỗi cache thành mất dữ liệu bền vững hoặc trả dữ liệu sai quyền.
- Không cache raw token, secret, file upload, PII không cần thiết hoặc response có
  ownership khác nhau dưới key dùng chung. Dữ liệu theo user phải scope key theo
  user và vẫn kiểm tra authorization.
- Lock/rate limit dùng atomic Redis operation và TTL. Không dùng distributed lock
  nếu DB uniqueness/transaction đã giải quyết được.

## Query và test

- Tránh N+1; select đúng cột cần dùng; pagination cho collection có thể tăng.
- Test constraint, rollback, concurrency/idempotency; test cache hit, miss,
  invalidation, TTL và hành vi khi Redis unavailable.
