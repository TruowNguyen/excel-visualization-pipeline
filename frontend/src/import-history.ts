type Attempt = Record<string, unknown>;
type HistoryView = {
  items: Attempt[]; loading: boolean; error: string; loadedAt: string | null;
  selectedAttempt: number | null; focusedAttempt: number | null;
  formatCell: (column: string, value: unknown) => string;
};
const escape = (value: unknown): string => String(value ?? '').replace(/[&<>"']/g,
  char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!);

/** Render only public values returned by the history endpoint; never infer a run or public ref. */
export function importHistoryContents(view: HistoryView): string {
  const cell = (key: string, value: unknown) => escape(view.formatCell(key, value));
  const detailFields: [string, string][] = [
    ['started_at', 'Bắt đầu lúc'], ['finished_at', 'Kết thúc lúc'], ['committed_at', 'Ghi dữ liệu lúc'],
    ['input_record_count', 'Điểm dữ liệu trong tệp'], ['inserted_count', 'Thêm mới'],
    ['updated_count', 'Cập nhật'], ['unchanged_count', 'Giữ nguyên'], ['restored_count', 'Khôi phục'],
    ['deleted_count', 'Không còn hiệu lực'], ['lineage_changed_count', 'Đổi nguồn tham chiếu'],
    ['error_count', 'Lỗi'], ['warning_count', 'Cảnh báo'], ['source_hash', 'Mã nhận diện tệp'],
  ];
  const status = view.loading ? 'Đang tải lịch sử nhập…' : view.loadedAt
    ? `Đã tải ${view.items.length} lần nhập · ${new Date(view.loadedAt).toLocaleString('vi-VN')}` : '';
  const missing = !view.loading && !view.error && view.focusedAttempt !== null
    && !view.items.some(item => Number(item.attempt_id) === view.focusedAttempt);
  return `<div class="history-toolbar"><p role="status" aria-live="polite">${escape(status)}</p><button id="history-refresh-action" class="ghost" data-action="retry-history">${view.loading ? 'Tải lại lịch sử' : 'Làm mới lịch sử'}</button></div>
    ${view.error ? `<div class="history-error" role="alert"><strong>Không tải được lịch sử nhập.</strong><p>${escape(view.error)} Kết quả nhập và tệp đang chọn vẫn được giữ. ${view.loadedAt ? 'Danh sách bên dưới là lần tải thành công gần nhất.' : ''}</p></div>` : ''}
    ${missing ? '<p class="history-not-found" role="status">Chưa tìm thấy lần nhập này trong tối đa 100 dòng đã tải. Kết quả ghi đã xác nhận vẫn được giữ; không cần nhập lại. Bạn có thể làm mới lịch sử.</p>' : ''}
    ${view.items.length ? `<div class="table-wrap history-table"><table><thead><tr><th>Bắt đầu lúc</th><th>Tệp Excel</th><th>Kết quả</th><th>Cách nhập</th><th>Thêm mới / cập nhật / giữ nguyên</th><th>Chi tiết</th></tr></thead><tbody>${view.items.map(item => {
      const id = Number(item.attempt_id);
      const expanded = view.selectedAttempt === id;
      const current = view.focusedAttempt === id;
      return `<tr id="history-row-${id}" tabindex="-1" ${current ? 'class="current-import" aria-current="true"' : ''}><td>${cell('started_at', item.started_at)}</td><td class="history-file" title="${escape(item.submitted_file_name)}">${escape(item.submitted_file_name || 'Chưa có tên tệp')}</td><td>${cell('attempt_status', item.attempt_status)}</td><td>${cell('requested_mode', item.requested_mode)}</td><td>${cell('inserted_count', item.inserted_count)} / ${cell('updated_count', item.updated_count)} / ${cell('unchanged_count', item.unchanged_count)}</td><td><button id="history-detail-${id}" class="text-action" data-action="history-detail" data-attempt-id="${id}" aria-expanded="${expanded}" aria-controls="history-details-${id}" aria-label="${expanded ? 'Thu gọn' : 'Xem'} chi tiết lần nhập ${id}">${expanded ? 'Thu gọn' : 'Chi tiết'}</button></td></tr>
        ${expanded ? `<tr class="history-detail-row" id="history-details-${id}"><td colspan="6"><dl class="history-detail-grid">${detailFields.map(([key, label]) => `<div><dt>${label}</dt><dd>${cell(key, item[key])}</dd></div>`).join('')}</dl>${item.duplicate_of_run_id != null ? '<p>Tệp đã được nhập trước đó; lần thử này không tạo một phiên dữ liệu mới.</p>' : ''}${item.failure_message ? `<p class="history-failure-message">${escape(item.failure_message)}</p>` : ''}</td></tr>` : ''}`;
    }).join('')}</tbody></table></div>` : view.loading ? '<p class="history-empty">Đang lấy các lần nhập gần nhất từ kho dữ liệu…</p>' : !view.error ? '<p class="history-empty">Chưa có lần nhập nào. Sau khi kiểm tra và xác nhận tệp Excel, kết quả sẽ xuất hiện ở đây.</p>' : ''}`;
}
