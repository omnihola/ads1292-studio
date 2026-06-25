#pragma once
#include <deque>
#include <mutex>

namespace ads1292 { namespace acq {

template <class T>
class SampleQueue {
 public:
  void push(const T& v) {
    std::lock_guard<std::mutex> lk(m_);
    q_.push_back(v);
  }

  bool try_pop(T& out) {
    std::lock_guard<std::mutex> lk(m_);
    if (q_.empty()) return false;
    out = q_.front();
    q_.pop_front();
    return true;
  }

  std::size_t size() const {
    std::lock_guard<std::mutex> lk(m_);
    return q_.size();
  }

 private:
  std::deque<T> q_;
  mutable std::mutex m_;
};

}}  // namespace ads1292::acq
