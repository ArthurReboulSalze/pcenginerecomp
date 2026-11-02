#include "pce/dev_server.hpp"
#include <algorithm>
#include <charconv>
#include <chrono>
#include <initializer_list>
#include <limits>
#include <map>
#include <stdexcept>
#include <string_view>
#include <utility>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

namespace pce {
namespace {
#ifdef _WIN32
using Socket = SOCKET;
constexpr Socket invalid_socket = INVALID_SOCKET;
void close_socket(Socket s) {
  if (s != invalid_socket)
    closesocket(s);
}
bool blocked() {
  const auto n = WSAGetLastError();
  return n == WSAEWOULDBLOCK;
}
void nonblocking(Socket s) {
  u_long one = 1;
  if (ioctlsocket(s, FIONBIO, &one))
    throw std::runtime_error("development socket nonblocking setup failed");
}
#else
using Socket = int;
constexpr Socket invalid_socket = -1;
void close_socket(Socket s) {
  if (s != invalid_socket)
    ::close(s);
}
bool blocked() {
  return errno == EWOULDBLOCK || errno == EAGAIN || errno == EINTR;
}
void nonblocking(Socket s) {
  const int flags = fcntl(s, F_GETFL, 0);
  if (flags < 0 || fcntl(s, F_SETFL, flags | O_NONBLOCK) < 0)
    throw std::runtime_error("development socket nonblocking setup failed");
}
#endif
using Clock = std::chrono::steady_clock;
constexpr std::size_t max_request = 8192, max_tx = 17 * 1024 * 1024,
                      io_budget = 64 * 1024;
constexpr std::uint64_t max_json_integer = 9007199254740991ULL;
struct Value {
  bool string = false;
  std::string text;
  std::uint64_t number = 0;
};
struct Parser {
  std::string_view text;
  std::size_t pos = 0;
  void ws() {
    while (pos < text.size() &&
           (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\r'))
      ++pos;
  }
  void take(char c) {
    ws();
    if (pos == text.size() || text[pos++] != c)
      throw std::runtime_error("invalid flat JSON request");
  }
  std::string str() {
    take('"');
    std::string out;
    while (pos < text.size()) {
      unsigned char c = static_cast<unsigned char>(text[pos++]);
      if (c == '"')
        return out;
      if (c < 32 || c >= 127)
        throw std::runtime_error("strings must contain ASCII JSON characters");
      if (c == '\\') {
        if (pos == text.size())
          break;
        c = static_cast<unsigned char>(text[pos++]);
        switch (c) {
        case '"':
        case '\\':
        case '/':
          out += static_cast<char>(c);
          break;
        case 'b':
          out += '\b';
          break;
        case 'f':
          out += '\f';
          break;
        case 'n':
          out += '\n';
          break;
        case 'r':
          out += '\r';
          break;
        case 't':
          out += '\t';
          break;
        case 'u': {
          unsigned v = 0;
          for (unsigned i = 0; i < 4; ++i) {
            if (pos == text.size())
              throw std::runtime_error("incomplete JSON escape");
            const char h = text[pos++];
            v *= 16;
            if (h >= '0' && h <= '9')
              v += h - '0';
            else if (h >= 'a' && h <= 'f')
              v += h - 'a' + 10;
            else if (h >= 'A' && h <= 'F')
              v += h - 'A' + 10;
            else
              throw std::runtime_error("invalid JSON escape");
          }
          if (v > 127)
            throw std::runtime_error("only ASCII JSON escapes are supported");
          out += static_cast<char>(v);
          break;
        }
        default:
          throw std::runtime_error("invalid JSON escape");
        }
      } else
        out += static_cast<char>(c);
    }
    throw std::runtime_error("unterminated JSON string");
  }
  std::map<std::string, Value> parse() {
    std::map<std::string, Value> out;
    take('{');
    ws();
    if (pos < text.size() && text[pos] == '}')
      ++pos;
    else
      for (;;) {
        auto key = str();
        take(':');
        ws();
        Value value;
        if (pos < text.size() && text[pos] == '"') {
          value.string = true;
          value.text = str();
        } else {
          const auto start = pos;
          while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9')
            ++pos;
          if (start == pos || (pos - start > 1 && text[start] == '0'))
            throw std::runtime_error("expected unsigned integer or string");
          const auto part = text.substr(start, pos - start);
          const auto r = std::from_chars(part.data(), part.data() + part.size(),
                                         value.number);
          if (r.ec != std::errc{} || value.number > max_json_integer)
            throw std::runtime_error("JSON integer exceeds exact range");
        }
        if (!out.emplace(std::move(key), std::move(value)).second)
          throw std::runtime_error("duplicate request field");
        if (out.size() > 6)
          throw std::runtime_error("too many request fields");
        ws();
        if (pos < text.size() && text[pos] == '}') {
          ++pos;
          break;
        }
        take(',');
      }
    ws();
    if (pos != text.size())
      throw std::runtime_error("trailing JSON text");
    return out;
  }
};
std::string quote(std::string_view s) {
  std::string out = "\"";
  constexpr char hex[] = "0123456789abcdef";
  for (unsigned char c : s) {
    if (c == '"' || c == '\\') {
      out += '\\';
      out += static_cast<char>(c);
    } else if (c < 32 || c >= 127) {
      out += "\\u00";
      out += hex[c >> 4];
      out += hex[c & 15];
    } else
      out += static_cast<char>(c);
  }
  return out + '"';
}
void append_base64(std::string &out, const std::vector<std::uint8_t> &bytes) {
  constexpr char chars[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  for (std::size_t n = 0; n < bytes.size(); n += 3) {
    const unsigned a = bytes[n], b = n + 1 < bytes.size() ? bytes[n + 1] : 0,
                   c = n + 2 < bytes.size() ? bytes[n + 2] : 0;
    out += chars[a >> 2];
    out += chars[((a & 3) << 4) | (b >> 4)];
    out += n + 1 < bytes.size() ? chars[((b & 15) << 2) | (c >> 6)] : '=';
    out += n + 2 < bytes.size() ? chars[c & 63] : '=';
  }
}
std::vector<std::uint8_t> decode_hex(std::string_view text) {
  if (text.empty() || text.size() > 512 || text.size() % 2)
    throw std::runtime_error("memory hex must contain 1..256 complete bytes");
  const auto nibble = [](char c) -> unsigned {
    if (c >= '0' && c <= '9')
      return static_cast<unsigned>(c - '0');
    if (c >= 'a' && c <= 'f')
      return static_cast<unsigned>(c - 'a' + 10);
    if (c >= 'A' && c <= 'F')
      return static_cast<unsigned>(c - 'A' + 10);
    throw std::runtime_error("memory data must contain only hex digits");
  };
  std::vector<std::uint8_t> out;
  out.reserve(text.size() / 2);
  for (std::size_t i = 0; i < text.size(); i += 2)
    out.push_back(static_cast<std::uint8_t>((nibble(text[i]) << 4) |
                                            nibble(text[i + 1])));
  return out;
}
std::string encode_hex(const std::vector<std::uint8_t> &bytes) {
  constexpr char digits[] = "0123456789abcdef";
  std::string out;
  out.reserve(bytes.size() * 2);
  for (const auto byte : bytes) {
    out += digits[byte >> 4];
    out += digits[byte & 15];
  }
  return out;
}
} // namespace

struct DevServer::Impl {
  Socket listener = invalid_socket, client = invalid_socket;
  std::uint16_t bound_port = 0;
  bool paused = false, stepping = false, quit = false, close_after_tx = false, resnapshot = false;
  std::uint64_t target_frame = 0;
  std::array<std::uint16_t, 5> input{};
  std::string rx, tx;
  std::size_t sent = 0;
  Clock::time_point idle = Clock::now(), request_started = idle,
                    tx_started = idle;
  bool request_pending = false;
#ifdef _WIN32
  bool winsock = false;
#endif
  explicit Impl(std::uint16_t port, bool start_paused) : paused(start_paused) {
    try {
#ifdef _WIN32
      WSADATA data{};
      if (WSAStartup(MAKEWORD(2, 2), &data))
        throw std::runtime_error("development Winsock initialization failed");
      winsock = true;
#endif
      listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
      if (listener == invalid_socket)
        throw std::runtime_error("development listener creation failed");
#ifdef _WIN32
      const BOOL exclusive = TRUE;
      if (setsockopt(listener, SOL_SOCKET, SO_EXCLUSIVEADDRUSE,
                     reinterpret_cast<const char *>(&exclusive),
                     sizeof(exclusive)))
        throw std::runtime_error(
            "development listener exclusive bind setup failed");
#endif
      nonblocking(listener);
      sockaddr_in address{};
      address.sin_family = AF_INET;
      address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
      address.sin_port = htons(port);
      if (bind(listener, reinterpret_cast<const sockaddr *>(&address),
               sizeof(address)) ||
          listen(listener, 1))
        throw std::runtime_error("development listener bind/listen failed");
#ifdef _WIN32
      int length = sizeof(address);
#else
      socklen_t length = sizeof(address);
#endif
      if (getsockname(listener, reinterpret_cast<sockaddr *>(&address),
                      &length))
        throw std::runtime_error("development listener address query failed");
      bound_port = ntohs(address.sin_port);
    } catch (...) {
      cleanup();
      throw;
    }
  }
  ~Impl() { cleanup(); }
  void cleanup() {
    close_socket(client);
    close_socket(listener);
    client = listener = invalid_socket;
#ifdef _WIN32
    if (winsock) {
      WSACleanup();
      winsock = false;
    }
#endif
  }
  void disconnect() {
    close_socket(client);
    client = invalid_socket;
    input.fill(0);
    rx.clear();
    std::string{}.swap(tx);
    sent = 0;
    request_pending = false;
    close_after_tx = false;
  }
  void respond(std::string value) {
    if (value.size() + 1 > max_tx)
      throw std::runtime_error("development response exceeds bounded buffer");
    tx = std::move(value);
    tx += '\n';
    sent = 0;
    tx_started = Clock::now();
  }
  void command(std::string_view line, const DevSnapshot &snapshot) {
    std::string id = "null";
    try {
      auto args = Parser{line}.parse();
      auto integer = [&](const char *key, std::uint64_t fallback,
                         bool required = false) {
        const auto i = args.find(key);
        if (i == args.end()) {
          if (required)
            throw std::runtime_error(std::string("missing ") + key);
          return fallback;
        }
        if (i->second.string)
          throw std::runtime_error(std::string("expected integer ") + key);
        return i->second.number;
      };
      auto string = [&](const char *key, std::string fallback,
                        bool required = false) {
        const auto i = args.find(key);
        if (i == args.end()) {
          if (required)
            throw std::runtime_error(std::string("missing ") + key);
          return fallback;
        }
        if (!i->second.string)
          throw std::runtime_error(std::string("expected string ") + key);
        return i->second.text;
      };
      id = std::to_string(integer("id", 0, true));
      const auto cmd = string("cmd", "", true);
      auto fields = [&](std::initializer_list<std::string_view> extra) {
        for (const auto &[key, value] : args) {
          (void)value;
          if (key == "id" || key == "cmd")
            continue;
          if (std::find(extra.begin(), extra.end(), key) == extra.end())
            throw std::runtime_error("unknown request field");
        }
      };
      std::string result;
      if (cmd == "ping") {
        fields({});
        result = "\"protocol\":\"pce-dev-1\"";
      } else if (cmd == "status") {
        fields({});
        result =
            "\"frame\":" + std::to_string(snapshot.frame) +
            ",\"ticks\":" + std::to_string(snapshot.ticks) + ",\"paused\":" +
            (snapshot.local_paused ||
                     (paused && (!stepping || snapshot.frame >= target_frame))
                 ? "true"
                 : "false") +
            ",\"local_paused\":" + (snapshot.local_paused ? "true" : "false") +
            ",\"host\":" + (snapshot.status ? snapshot.status() : "{}");
      } else if (cmd == "set_input") {
        fields({"mask", "port"});
        const auto mask = integer("mask", 0, true), port = integer("port", 0);
        if (mask > 0xfff || port > 4)
          throw std::runtime_error("input mask or port out of range");
        input[port] = static_cast<std::uint16_t>(mask);
        if(snapshot.apply_input) snapshot.apply_input();
      } else if (cmd == "clear_input") {
        fields({"port"});
        if (args.contains("port")) {
          const auto port = integer("port", 0);
          if (port > 4)
            throw std::runtime_error("input port out of range");
          input[port] = 0;
        } else
          input.fill(0);
        if(snapshot.apply_input) snapshot.apply_input();
      } else if (cmd == "pause") {
        fields({});
        paused = true;
        stepping = false;
      } else if (cmd == "resume") {
        fields({});
        if (snapshot.reference_selected)
          throw std::runtime_error("reference execution requires bounded reference_frames");
        paused = false;
        stepping = false;
      } else if (cmd == "step_frames" || cmd == "reference_frames") {
        fields({"frames"});
        const bool reference = cmd == "reference_frames";
        if (!reference && snapshot.reference_selected)
          throw std::runtime_error("reference execution requires reference_frames");
        if (reference && (!paused || (stepping && snapshot.frame < target_frame)))
          throw std::runtime_error("reference execution requires a quiescent remote pause");
        if (snapshot.local_paused)
          throw std::runtime_error(
              "release the local desktop pause before stepping frames");
        const auto count = integer("frames", 0, true);
        if (count < 1 || count > 600 ||
            snapshot.frame > std::numeric_limits<std::uint64_t>::max() - count)
          throw std::runtime_error("frame count out of range");
        if (reference) {
          if (!snapshot.reference_frames)
            throw std::runtime_error("reference execution requires explicit host opt-in");
          snapshot.reference_frames();
          // Resnapshot policy before handling any pipelined command.
          resnapshot = true;
        }
        paused = true;
        stepping = true;
        target_frame = snapshot.frame + count;
        result = "\"target_frame\":" + std::to_string(target_frame);
      } else if (cmd == "save_checkpoint" || cmd == "load_checkpoint") {
        fields({"name"});
        if ((!snapshot.local_paused && !paused) || (stepping && snapshot.frame < target_frame))
          throw std::runtime_error("checkpoints require a quiescent pause");
        const auto& callback=cmd=="save_checkpoint" ? snapshot.save_checkpoint:snapshot.load_checkpoint;
        if(!callback) throw std::runtime_error("developer checkpoints require explicit host opt-in");
        result="\"checkpoint\":"+callback(string("name","",true));
        if(cmd=="load_checkpoint") {paused=true;stepping=false;resnapshot=true;}
      } else if (cmd == "capture_summary" || cmd == "capture_sources") {
        fields(cmd == "capture_summary"
                   ? std::initializer_list<std::string_view>{}
                   : std::initializer_list<std::string_view>{"offset", "limit", "retired"});
        if ((!snapshot.local_paused && !paused) ||
            (stepping && snapshot.frame < target_frame))
          throw std::runtime_error("code-capture inspection requires a quiescent pause");
        if (cmd == "capture_summary") {
          if (!snapshot.capture_summary)
            throw std::runtime_error("code-capture inspection unavailable");
          result = "\"capture\":" + snapshot.capture_summary();
        } else {
          const auto offset = integer("offset", 0, true);
          const auto limit = integer("limit", 0, true);
          const auto retired = integer("retired", 0, true);
          if (offset > 65536 || limit < 1 || limit > 256)
            throw std::runtime_error("code-capture page out of bounds");
          if (!snapshot.capture_sources)
            throw std::runtime_error("code capture disabled");
          result = "\"capture\":" + snapshot.capture_sources(
              retired, static_cast<std::uint32_t>(offset), static_cast<std::uint32_t>(limit));
        }
      } else if (cmd == "read_memory" || cmd == "write_memory") {
        fields(
            cmd == "read_memory"
                ? std::initializer_list<std::string_view>{"address", "length"}
                : std::initializer_list<std::string_view>{"address", "data",
                                                          "expected"});
        const auto address = integer("address", 0, true);
        std::vector<std::uint8_t> data, expected;
        std::uint64_t length = 0;
        if (cmd == "read_memory") {
          length = integer("length", 0, true);
        } else {
          data = decode_hex(string("data", "", true));
          expected = decode_hex(string("expected", "", true));
          length = data.size();
          if (expected.size() != data.size())
            throw std::runtime_error("memory data and expected lengths differ");
        }
        if (length < 1 || length > 256 || address >= 0x200000 ||
            length > 0x200000 - address)
          throw std::runtime_error("memory address or length out of range");
        if ((!snapshot.local_paused && !paused) ||
            (stepping && snapshot.frame < target_frame))
          throw std::runtime_error("memory access requires a quiescent pause");
        result = "\"address\":" + std::to_string(address) +
                 ",\"length\":" + std::to_string(length);
        if (cmd == "read_memory") {
          if (!snapshot.read_memory)
            throw std::runtime_error("memory reads disabled");
          data = snapshot.read_memory(static_cast<std::uint32_t>(address),
                                      static_cast<std::uint32_t>(length));
          if (data.size() != length)
            throw std::runtime_error(
                "memory read callback returned wrong length");
          result += ",\"data\":" + quote(encode_hex(data));
        } else {
          if (!snapshot.write_memory)
            throw std::runtime_error("memory writes disabled");
          snapshot.write_memory(static_cast<std::uint32_t>(address), data,
                                expected);
        }
      } else if (cmd == "quit") {
        fields({});
        quit = true;
        input.fill(0);
      } else if (cmd == "screenshot" || cmd == "present_shot") {
        fields(cmd == "screenshot"
                   ? std::initializer_list<std::string_view>{"source"}
                   : std::initializer_list<std::string_view>{});
        const auto source = cmd == "present_shot" ? std::string("present")
                                                  : string("source", "guest");
        if (source != "guest" && source != "present")
          throw std::runtime_error("unknown screenshot source");
        if (!snapshot.capture)
          throw std::runtime_error("capture unavailable");
        const bool present = source == "present";
        auto frame = snapshot.capture(present);
        const auto pixels = std::uint64_t(frame.width) * frame.height;
        if (!frame.width || !frame.height ||
            pixels > (present ? 4000000ULL : 1024ULL * 512) ||
            (!present && (frame.width > 1024 || frame.height > 512)) ||
            frame.rgb.size() != pixels * 3)
          throw std::runtime_error(
              "capture dimensions or RGB byte count out of range");
        result = "\"source\":" + quote(source) +
                 ",\"width\":" + std::to_string(frame.width) +
                 ",\"height\":" + std::to_string(frame.height) +
                 ",\"frame\":" + std::to_string(snapshot.frame) +
                 ",\"ticks\":" + std::to_string(snapshot.ticks) +
                 ",\"frame_ticks\":" + std::to_string(snapshot.frame_ticks) +
                 ",\"encoding\":\"rgb24-base64\",\"data\":\"";
        // One RGB copy plus one final encoded response; no intermediate
        // full-size base64 string or second response allocation.
        result.reserve(result.size() + ((frame.rgb.size() + 2) / 3) * 4 + 128);
        append_base64(result, frame.rgb);
        result += '"';
      } else
        throw std::runtime_error("unknown command");
      result.insert(0, "{\"id\":" + id + ",\"ok\":true" +
                           (result.empty() ? "" : ","));
      result += '}';
      respond(std::move(result));
    } catch (const std::exception &e) {
      respond("{\"id\":" + id + ",\"ok\":false,\"error\":" + quote(e.what()) +
              "}");
    }
  }
  void poll(const DevSnapshot &snapshot) {
    if (client == invalid_socket) {
      sockaddr_in peer{};
#ifdef _WIN32
      int length = sizeof(peer);
#else
      socklen_t length = sizeof(peer);
#endif
      const auto accepted =
          accept(listener, reinterpret_cast<sockaddr *>(&peer), &length);
      if (accepted == invalid_socket)
        return;
      if (peer.sin_family != AF_INET ||
          ntohl(peer.sin_addr.s_addr) != INADDR_LOOPBACK) {
        close_socket(accepted);
        return;
      }
      try {
        nonblocking(accepted);
      } catch (...) {
        close_socket(accepted);
        throw;
      }
#ifdef SO_NOSIGPIPE
      int one = 1;
      if (setsockopt(accepted, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one))) {
        close_socket(accepted);
        throw std::runtime_error("development socket signal setup failed");
      }
#endif
      client = accepted;
      idle = Clock::now();
    }
    const auto now = Clock::now();
    if (now - idle > std::chrono::seconds(5) ||
        (request_pending && now - request_started > std::chrono::seconds(5)) ||
        (!tx.empty() && now - tx_started > std::chrono::seconds(5))) {
      disconnect();
      return;
    }
    std::size_t budget = io_budget;
    while (budget && client != invalid_socket) {
      if (!tx.empty()) {
        const auto count = static_cast<int>(std::min(budget, tx.size() - sent));
#ifdef MSG_NOSIGNAL
        const int flags = MSG_NOSIGNAL;
#else
        const int flags = 0;
#endif
        const auto n = send(client, tx.data() + sent, count, flags);
        if (n < 0) {
          if (blocked())
            return;
          disconnect();
          return;
        }
        if (n == 0) {
          disconnect();
          return;
        }
        sent += static_cast<std::size_t>(n);
        budget -= static_cast<std::size_t>(n);
        idle = Clock::now();
        if (sent != tx.size())
          continue;
        std::string{}.swap(tx);
        sent = 0;
        if (close_after_tx) {
          disconnect();
          return;
        }
        if(resnapshot) {resnapshot=false;return;}
      }
      const auto newline = rx.find('\n');
      if (newline != std::string::npos) {
        const auto line = rx.substr(0, newline);
        rx.erase(0, newline + 1);
        request_pending = !rx.empty();
        request_started = Clock::now();
        command(line, snapshot);
        continue;
      }
      if (rx.size() == max_request) {
        respond("{\"id\":null,\"ok\":false,\"error\":\"request exceeds 8192 "
                "bytes\"}");
        close_after_tx = true;
        continue;
      }
      char bytes[4096];
      const auto capacity =
          std::min({sizeof(bytes), budget, max_request - rx.size()});
      const auto n = recv(client, bytes, static_cast<int>(capacity), 0);
      if (n < 0) {
        if (blocked())
          return;
        disconnect();
        return;
      }
      if (n == 0) {
        disconnect();
        return;
      }
      if (!request_pending) {
        request_started = Clock::now();
        request_pending = true;
      }
      rx.append(bytes, static_cast<std::size_t>(n));
      budget -= static_cast<std::size_t>(n);
      idle = Clock::now();
    }
  }
};
DevServer::DevServer(std::uint16_t port, bool start_paused)
    : impl_(std::make_unique<Impl>(port, start_paused)) {}
DevServer::~DevServer() = default;
std::uint16_t DevServer::port() const { return impl_->bound_port; }
void DevServer::poll(const DevSnapshot &snapshot) { impl_->poll(snapshot); }
bool DevServer::paused(std::uint64_t frame) const {
  return impl_->paused && (!impl_->stepping || frame >= impl_->target_frame);
}
const std::array<std::uint16_t, 5> &DevServer::input_masks() const {
  return impl_->input;
}
void DevServer::restore_input_masks(const std::array<std::uint16_t,5>& masks) {
  for(auto mask:masks) if(mask>4095) throw std::runtime_error("invalid checkpoint remote input");
  impl_->input=masks;
}
bool DevServer::quit_requested() const { return impl_->quit; }
} // namespace pce
