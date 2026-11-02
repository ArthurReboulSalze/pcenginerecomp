#include "pce/dev_server.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
using Socket = SOCKET;
static constexpr Socket bad = INVALID_SOCKET;
static void close_socket(Socket s) { closesocket(s); }
#else
#include <arpa/inet.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>
using Socket = int;
static constexpr Socket bad = -1;
static void close_socket(Socket s) { ::close(s); }
#endif

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
struct Peer {
  Socket s = bad;
  std::string received;
  explicit Peer(std::uint16_t port) {
    s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    require(s != bad, "client creation failed");
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (connect(s, reinterpret_cast<sockaddr *>(&a), sizeof(a))) {
      close_socket(s);
      throw std::runtime_error("client connection failed");
    }
#ifdef _WIN32
    u_long one = 1;
    require(ioctlsocket(s, FIONBIO, &one) == 0, "client nonblocking failed");
#else
    require(fcntl(s, F_SETFL, fcntl(s, F_GETFL, 0) | O_NONBLOCK) == 0,
            "client nonblocking failed");
#endif
  }
  ~Peer() {
    if (s != bad)
      close_socket(s);
  }
  void close() {
    close_socket(s);
    s = bad;
  }
  void send(const std::string &text) {
    std::size_t n = 0;
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (n < text.size()) {
      const auto count =
          ::send(s, text.data() + n, static_cast<int>(text.size() - n), 0);
      if (count > 0)
        n += static_cast<std::size_t>(count);
      else
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      require(std::chrono::steady_clock::now() < deadline,
              "client send timed out");
    }
  }
  std::string response(pce::DevServer &server,
                       const pce::DevSnapshot &snapshot) {
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(3);
    for (;;) {
      server.poll(snapshot);
      char buffer[4096];
      const auto count = recv(s, buffer, sizeof(buffer), 0);
      if (count > 0)
        received.append(buffer, static_cast<std::size_t>(count));
      const auto newline = received.find('\n');
      if (newline != std::string::npos) {
        auto line = received.substr(0, newline);
        received.erase(0, newline + 1);
        return line;
      }
      require(std::chrono::steady_clock::now() < deadline,
              "response timed out");
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
  }
  std::string call(pce::DevServer &server, const pce::DevSnapshot &snapshot,
                   const std::string &request) {
    send(request + "\n");
    return response(server, snapshot);
  }
};
static bool has(const std::string &text, const std::string &part) {
  return text.find(part) != std::string::npos;
}

static unsigned memory_checks(pce::DevServer &server,
                              const pce::DevSnapshot &base) {
  unsigned checks = 0, reads = 0, writes = 0;
  constexpr std::uint32_t start = 0x1ffe00;
  std::vector<std::uint8_t> memory(512);
  for (unsigned i = 0; i < memory.size(); ++i)
    memory[i] = static_cast<std::uint8_t>(i);
  const auto original = memory;
  auto state = base;
  state.read_memory = [&](std::uint32_t address, std::uint32_t length) {
    ++reads;
    if (address < start || address - start + length > memory.size())
      throw std::runtime_error("authored read region refusal");
    return std::vector<std::uint8_t>(memory.begin() + (address - start),
                                     memory.begin() +
                                         (address - start + length));
  };
  state.write_memory = [&](std::uint32_t address,
                           const std::vector<std::uint8_t> &data,
                           const std::vector<std::uint8_t> &expected) {
    ++writes;
    if (address < start || address - start + data.size() > memory.size())
      throw std::runtime_error("authored write region refusal");
    const auto at = memory.begin() + (address - start);
    if (!std::equal(expected.begin(), expected.end(), at))
      throw std::runtime_error("authored expected bytes mismatch");
    std::copy(data.begin(), data.end(), at);
  };
  const std::string prefix = "{\"id\":300,\"cmd\":";
  const std::string read =
      prefix + "\"read_memory\",\"address\":" + std::to_string(start) +
      ",\"length\":3}";
  const auto write = [&](const std::string &data, const std::string &expected) {
    return prefix + "\"write_memory\",\"address\":" + std::to_string(start) +
           ",\"data\":\"" + data + "\",\"expected\":\"" + expected + "\"}";
  };
  {
    Peer peer(server.port());
    const auto reply = peer.call(server, state, read);
    require(has(reply, "\"address\":2096640,\"length\":3") &&
                has(reply, "\"data\":\"000102\"") && reads == 1 &&
                writes == 0 && memory == original,
            "paused memory read shape or side effects failed");
    ++checks;
    std::string hex;
    constexpr char digits[] = "0123456789abcdef";
    for (unsigned i = 0; i < 256; ++i) {
      hex += digits[i >> 4];
      hex += digits[i & 15];
    }
    require(
        has(peer.call(
                server, state,
                prefix + "\"read_memory\",\"address\":2096896,\"length\":256}"),
            "\"data\":\"" + hex + "\"") &&
            reads == 2,
        "maximum memory read at physical end failed");
    ++checks;
    require(has(peer.call(server, state, write("FfAa00", "000102")),
                "\"ok\":true,\"address\":2096640,\"length\":3") &&
                writes == 1 && memory[0] == 255 && memory[1] == 170 &&
                memory[2] == 0 && memory[3] == 3,
            "compare-before-write decoded bytes or response failed");
    ++checks;
    const auto changed = memory;
    require(has(peer.call(server, state, write("111213", "000000")),
                "authored expected bytes mismatch") &&
                writes == 2 && memory == changed,
            "expected mismatch not delegated or changed bytes");
    ++checks;
    const auto before_reads = reads, before_writes = writes;
    for (const auto &bad : std::vector<std::string>{
             prefix + "\"read_memory\"}",
             prefix + "\"read_memory\",\"address\":0}",
             prefix + "\"read_memory\",\"address\":0,\"length\":0}",
             prefix + "\"read_memory\",\"address\":0,\"length\":257}",
             prefix + "\"read_memory\",\"address\":2097152,\"length\":1}",
             prefix + "\"read_memory\",\"address\":2097151,\"length\":2}",
             prefix +
                 "\"read_memory\",\"address\":9007199254740991,\"length\":1}",
             prefix + "\"read_memory\",\"address\":\"0\",\"length\":1}",
             prefix + "\"read_memory\",\"address\":0,\"length\":\"1\"}",
             prefix +
                 "\"read_memory\",\"address\":0,\"length\":1,\"data\":\"00\"}",
             prefix +
                 "\"read_memory\",\"address\":0,\"length\":1,\"length\":2}",
             prefix + "\"write_memory\",\"address\":0,\"data\":\"00\"}",
             prefix + "\"write_memory\",\"data\":\"00\",\"expected\":\"00\"}",
             prefix + "\"write_memory\",\"address\":0,\"data\":0,\"expected\":"
                      "\"00\"}",
             prefix + "\"write_memory\",\"address\":0,\"data\":\"00\","
                      "\"expected\":0}",
             prefix + "\"write_memory\",\"address\":0,\"data\":\"00\","
                      "\"expected\":\"00\",\"length\":1}",
             prefix + "\"write_memory\",\"address\":2097152,\"data\":\"00\","
                      "\"expected\":\"00\"}",
             prefix + "\"write_memory\",\"address\":2097151,\"data\":\"0000\","
                      "\"expected\":\"0000\"}",
             write("", ""),
             write("0", "0"),
             write("gg", "00"),
             write("00", "0x"),
             write(" 0", "00"),
             write("00", "00 0"),
             write("0000", "00"),
             write("00", "0000"),
             write(std::string(514, '0'), std::string(514, '0'))}) {
      require(has(peer.call(server, state, bad), "\"ok\":false") &&
                  reads == before_reads && writes == before_writes &&
                  memory == changed && server.paused(state.frame) &&
                  !server.quit_requested() &&
                  server.input_masks() == std::array<std::uint16_t, 5>{},
              "invalid memory request invoked callback or mutated state");
      ++checks;
    }
    auto disabled = state;
    disabled.read_memory = {};
    disabled.write_memory = {};
    require(has(peer.call(server, disabled, read), "memory reads disabled") &&
                has(peer.call(server, disabled, write("000102", "ffaa00")),
                    "memory writes disabled") &&
                reads == before_reads && writes == before_writes &&
                memory == changed,
            "missing memory callbacks not explicitly disabled");
    checks += 2;
    require(
        has(peer.call(server, state,
                      prefix + "\"read_memory\",\"address\":0,\"length\":1}"),
            "authored read region refusal") &&
            reads == before_reads + 1 && memory == changed,
        "read callback exception escaped or changed state");
    ++checks;
    require(has(peer.call(server, state,
                          prefix + "\"write_memory\",\"address\":0,\"data\":"
                                   "\"01\",\"expected\":\"00\"}"),
                "authored write region refusal") &&
                writes == before_writes + 1 && memory == changed,
            "write callback exception escaped or changed state");
    ++checks;
    for (const unsigned size : {0U, 2U, 4U, 257U}) {
      auto malformed = state;
      malformed.read_memory = [=](std::uint32_t, std::uint32_t) {
        return std::vector<std::uint8_t>(size, 0);
      };
      require(has(peer.call(server, malformed, read), "wrong length") &&
                  memory == changed,
              "wrong-sized callback result accepted");
      ++checks;
    }
    peer.call(server, state, "{\"id\":301,\"cmd\":\"resume\"}");
    auto local = state;
    local.local_paused = true;
    const auto pause_reads = reads, pause_writes = writes;
    require(has(peer.call(server, state, read), "quiescent pause") &&
                has(peer.call(server, state, write("000102", "ffaa00")),
                    "quiescent pause") &&
                reads == pause_reads && writes == pause_writes &&
                memory == changed,
            "running memory access invoked callbacks");
    checks += 2;
    require(has(peer.call(server, local, read), "\"data\":\"ffaa00\"") &&
                !server.paused(state.frame),
            "local pause memory read refused or changed server pause");
    ++checks;
    require(has(peer.call(server, local, write("000102", "ffaa00")),
                "\"ok\":true") &&
                memory == original && !server.paused(state.frame),
            "local pause memory write refused or changed server pause");
    ++checks;
    peer.call(server, state,
              "{\"id\":302,\"cmd\":\"step_frames\",\"frames\":3}");
    const auto step_reads = reads, step_writes = writes;
    require(has(peer.call(server, state, read), "quiescent pause") &&
                has(peer.call(server, state, write("ffaa00", "000102")),
                    "quiescent pause") &&
                has(peer.call(server, local, read), "quiescent pause") &&
                has(peer.call(server, local, write("ffaa00", "000102")),
                    "quiescent pause") &&
                reads == step_reads && writes == step_writes &&
                memory == original,
            "pending step allowed memory callback despite pause");
    checks += 4;
    auto completed = state;
    completed.frame += 3;
    require(has(peer.call(server, completed, read), "\"data\":\"000102\"") &&
                server.paused(completed.frame),
            "reached frame target did not allow quiescent read");
    ++checks;
    require(
        has(peer.call(server, completed,
                      prefix +
                          "\"write_memory\",\"address\":2096896,\"data\":\"" +
                          hex + "\",\"expected\":\"" + hex + "\"}"),
            "\"ok\":true,\"address\":2096896,\"length\":256") &&
            memory == original,
        "maximum compare-write at physical end failed");
    ++checks;
    require(
        has(peer.call(server, completed,
                      prefix +
                          "\"read_memory\",\"address\":2097151,\"length\":1}"),
            "\"data\":\"ff\""),
        "last physical byte read failed");
    ++checks;
    peer.call(server, state, "{\"id\":303,\"cmd\":\"pause\"}");
  }
  for (unsigned i = 0; i < 10; ++i)
    server.poll(base);
  return checks;
}

static unsigned live_capture_checks(pce::DevServer& server,const pce::DevSnapshot& base) {
  unsigned checks=0,summaries=0,pages=0;
  auto state=base;
  state.capture_summary=[&]{++summaries;return "{\"enabled\":true}";};
  state.capture_sources=[&](std::uint64_t retired,std::uint32_t offset,std::uint32_t limit) {
    ++pages;
    if(retired!=7)throw std::runtime_error("authored stale token");
    if(offset!=65536 || limit!=256)throw std::runtime_error("authored page bounds");
    return "{\"sources\":[]}";
  };
  {
    Peer peer(server.port());
    const std::string summary="{\"id\":400,\"cmd\":\"capture_summary\"}";
    const std::string page="{\"id\":401,\"cmd\":\"capture_sources\",\"offset\":65536,\"limit\":256,\"retired\":7}";
    require(has(peer.call(server,state,summary),"\"capture\":{\"enabled\":true}")&&summaries==1,"capture summary callback failed");++checks;
    require(has(peer.call(server,state,page),"\"capture\":{\"sources\":[]}")&&pages==1,"capture maximum page failed");++checks;
    for(const auto& request:std::vector<std::string>{
      "{\"id\":1,\"cmd\":\"capture_summary\",\"offset\":0}",
      "{\"id\":1,\"cmd\":\"capture_sources\"}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":1}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":0,\"retired\":7}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":257,\"retired\":7}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":65537,\"limit\":1,\"retired\":7}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":1,\"retired\":9007199254740992}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":1,\"retired\":true}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":\"0\",\"limit\":1,\"retired\":7}",
      "{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":0,\"limit\":1,\"retired\":7,\"data\":\"00\"}"}) {
      require(has(peer.call(server,state,request),"\"ok\":false")&&summaries==1&&pages==1,"invalid capture request invoked callback");++checks;
    }
    require(has(peer.call(server,state,"{\"id\":1,\"cmd\":\"capture_sources\",\"offset\":65536,\"limit\":256,\"retired\":6}"),"authored stale token")&&pages==2,"stale capture callback escaped");++checks;
    auto unavailable=base;
    require(has(peer.call(server,unavailable,summary),"inspection unavailable")&&has(peer.call(server,unavailable,page),"code capture disabled"),"missing capture callbacks accepted");checks+=2;
    peer.call(server,state,"{\"id\":1,\"cmd\":\"resume\"}");
    require(has(peer.call(server,state,summary),"quiescent pause")&&has(peer.call(server,state,page),"quiescent pause")&&summaries==1&&pages==2,"running inspection invoked callback");checks+=2;
    auto local=state;local.local_paused=true;
    require(has(peer.call(server,local,summary),"\"ok\":true")&&!server.paused(state.frame),"local paused inspection refused");++checks;
    peer.call(server,state,"{\"id\":1,\"cmd\":\"step_frames\",\"frames\":3}");
    require(has(peer.call(server,local,summary),"quiescent pause")&&has(peer.call(server,state,page),"quiescent pause")&&summaries==2&&pages==2,"pending step inspected capture");checks+=2;
    auto done=state;done.frame+=3;
    require(has(peer.call(server,done,page),"\"ok\":true")&&pages==3,"reached target capture refused");++checks;
    peer.call(server,state,"{\"id\":1,\"cmd\":\"pause\"}");
    require(server.input_masks()==std::array<std::uint16_t,5>{}&&!server.quit_requested(),"capture inspection mutated input/quit");++checks;
  }
  for(unsigned i=0;i<10;++i)server.poll(base);
  return checks;
}

static unsigned reference_checks() {
  pce::DevServer server(0, true);
  pce::DevSnapshot state;
  state.frame = 10;
  Peer peer(server.port());
  const auto call = [&](const std::string& command) {
    return peer.call(server, state, "{\"id\":800,\"cmd\":" + command + "}");
  };
  unsigned calls = 0;
  require(has(call("\"reference_frames\",\"frames\":1"), "explicit host opt-in"),
          "reference request without capability accepted");
  state.reference_frames = [&] { ++calls; state.reference_selected = true; };
  for (const auto& frames : {"0", "601", "true", "1.0", "-1"})
    require(has(call(std::string("\"reference_frames\",\"frames\":") + frames), "\"ok\":false"),
            "invalid reference frame count accepted");
  require(calls == 0 && server.paused(10), "invalid reference request changed policy/pause");
  require(has(call("\"resume\""), "\"ok\":true"), "authored resume refused");
  require(has(call("\"reference_frames\",\"frames\":1"), "quiescent remote pause") && calls == 0,
          "running reference request selected policy");
  call("\"pause\"");
  state.local_paused = true;
  require(has(call("\"reference_frames\",\"frames\":1"), "local desktop pause") && calls == 0,
          "local pause accepted reference stepping");
  state.local_paused = false;
  state.reference_frames = [&] { throw std::runtime_error("authored first-dispatch refusal"); };
  require(has(call("\"reference_frames\",\"frames\":1"), "first-dispatch refusal") && server.paused(10),
          "reference callback refusal changed stepping");
  state.reference_frames = [&] { ++calls; state.reference_selected = true; };
  require(has(call("\"reference_frames\",\"frames\":2"), "\"target_frame\":12") && calls == 1 && !server.paused(10),
          "valid reference selection did not start bounded step");
  require(has(call("\"reference_frames\",\"frames\":1"), "quiescent remote pause") && calls == 1,
          "active reference step accepted another request");
  state.frame = 12;
  require(server.paused(12), "reference target did not return paused");
  for (const auto& command : {"\"resume\"", "\"step_frames\",\"frames\":1"})
    require(has(call(command), "\"ok\":false") && server.paused(12), "reference escaped into normal execution");
  require(has(call("\"reference_frames\",\"frames\":1"), "\"target_frame\":13") && calls == 2,
          "same reference policy could not advance another bounded segment");
  state.frame = 13;
  return 16;
}

int main() {
  try {
    unsigned checks = 0, captures = 0, status_calls = 0;
    checks += reference_checks();
    pce::DevServer server(0, true);
    require(server.port() != 0 && server.paused(0),
            "automatic port or initial pause failed");
    ++checks;
    bool exclusive = false;
    try {
      pce::DevServer duplicate(server.port());
    } catch (const std::exception &) {
      exclusive = true;
    }
    require(exclusive, "listener allowed duplicate bind");
    ++checks;
    pce::DevSnapshot state;
    state.frame = 12;
    state.ticks = 345;
    state.frame_ticks = 340;
    state.status = [&] {
      ++status_calls;
      return "{\"native_steps\":7}";
    };
    state.capture = [&](bool present) {
      ++captures;
      return pce::VideoFrame{
          present ? 1U : 2U, present ? 2U : 1U, {0, 1, 2, 253, 254, 255}};
    };
    checks += memory_checks(server, state);
    checks += live_capture_checks(server, state);
    {
      Peer peer(server.port());
      peer.send("{\"id\":1,\"cmd\":\"set_in");
      for (unsigned n = 0; n < 3; ++n)
        server.poll(state);
      require(server.input_masks()[0] == 0,
              "fragment changed state before complete request");
      ++checks;
      peer.send("put\",\"mask\":4095}\n");
      require(has(peer.response(server, state), "\"ok\":true") &&
                  server.input_masks()[0] == 4095,
              "fragmented request failed");
      ++checks;
      peer.send("{\"id\":2,\"cmd\":\"ping\"}\n{\"id\":3,\"cmd\":\"status\"}\n");
      require(has(peer.response(server, state), "\"protocol\":\"pce-dev-1\""),
              "pipelined ping failed");
      const auto status = peer.response(server, state);
      require(has(status, "\"id\":3") && has(status, "\"frame\":12") &&
                  has(status, "\"ticks\":345") &&
                  has(status, "\"paused\":true") &&
                  has(status, "\"native_steps\":7") && status_calls == 1 &&
                  captures == 0,
              "lazy status failed");
      checks += 2;
      for (unsigned port = 0; port < 5; ++port) {
        const auto response =
            peer.call(server, state,
                      "{\"id\":4,\"cmd\":\"set_input\",\"mask\":" +
                          std::to_string(1U << port) +
                          ",\"port\":" + std::to_string(port) + "}");
        require(has(response, "\"ok\":true") &&
                    server.input_masks()[port] == (1U << port),
                "input port failed");
        ++checks;
      }
      require(has(peer.call(server, state,
                            "{\"id\":5,\"cmd\":\"clear_input\",\"port\":2}"),
                  "\"ok\":true") &&
                  server.input_masks()[2] == 0 && server.input_masks()[1] == 2,
              "selective input clear failed");
      ++checks;
      require(
          has(peer.call(server, state, "{\"id\":6,\"cmd\":\"clear_input\"}"),
              "\"ok\":true") &&
              server.input_masks() == std::array<std::uint16_t, 5>{},
          "all input clear failed");
      ++checks;
      require(has(peer.call(server, state,
                            "{\"id\":7,\"cmd\":\"step_frames\",\"frames\":3}"),
                  "\"target_frame\":15") &&
                  !server.paused(12) && !server.paused(14) && server.paused(15),
              "frame stepping boundary failed");
      ++checks;
      peer.call(server, state, "{\"id\":8,\"cmd\":\"resume\"}");
      require(!server.paused(0) && !server.paused(100), "resume failed");
      ++checks;
      auto locally_paused = state;
      locally_paused.local_paused = true;
      auto local_status =
          peer.call(server, locally_paused, "{\"id\":8,\"cmd\":\"status\"}");
      require(has(local_status, "\"paused\":true") &&
                  has(local_status, "\"local_paused\":true"),
              "local pause absent from aggregate status");
      ++checks;
      require(has(peer.call(server, locally_paused,
                            "{\"id\":8,\"cmd\":\"step_frames\",\"frames\":1}"),
                  "release the local desktop pause") &&
                  !server.paused(100),
              "local pause frame-step refusal mutated network state");
      ++checks;
      peer.call(server, locally_paused, "{\"id\":8,\"cmd\":\"resume\"}");
      require(has(peer.call(server, locally_paused,
                            "{\"id\":8,\"cmd\":\"status\"}"),
                  "\"paused\":true") &&
                  !server.paused(12),
              "network resume overrode local pause");
      ++checks;
      peer.call(server, state, "{\"id\":9,\"cmd\":\"pause\"}");
      require(server.paused(12), "pause failed");
      ++checks;
      const auto guest =
          peer.call(server, state, "{\"id\":10,\"cmd\":\"screenshot\"}");
      require(has(guest, "\"source\":\"guest\"") &&
                  has(guest, "\"width\":2,\"height\":1") &&
                  has(guest, "\"encoding\":\"rgb24-base64\"") &&
                  has(guest, "\"data\":\"AAEC/f7/\"") &&
                  has(guest, "\"frame_ticks\":340") && captures == 1,
              "guest RGB response failed");
      ++checks;
      require(
          has(peer.call(server, state, "{\"id\":11,\"cmd\":\"present_shot\"}"),
              "\"source\":\"present\"") &&
              captures == 2,
          "present capture alias failed");
      ++checks;
      require(
          has(peer.call(
                  server, state,
                  "{\"id\":12,\"cmd\":\"screenshot\",\"source\":\"present\"}"),
              "\"height\":2") &&
              captures == 3,
          "explicit present capture failed");
      ++checks;
      require(has(peer.call(
                      server, state,
                      "{\"id\":9007199254740991,\"c\\u006dd\":\"pi\\u006eg\"}"),
                  "\"id\":9007199254740991,\"ok\":true"),
              "ASCII JSON escapes or exact max id failed");
      ++checks;
      std::string exact = "{\"id\":14,\"cmd\":\"ping\"}";
      exact.append(8191 - exact.size(), ' ');
      require(has(peer.call(server, state, exact), "\"id\":14,\"ok\":true"),
              "maximum request including newline rejected");
      ++checks;
      for (const std::string &invalid :
           {"{}",
            "{\"cmd\":\"ping\"}",
            "{\"id\":1}",
            "{\"id\":1,\"id\":2,\"cmd\":\"ping\"}",
            "{\"id\":1,\"cmd\":\"ping\",\"cmd\":\"quit\"}",
            "{\"id\":1,\"cmd\":\"quit\",\"extra\":0}",
            "{\"id\":-1,\"cmd\":\"ping\"}",
            "{\"id\":1.5,\"cmd\":\"ping\"}",
            "{\"id\":1e0,\"cmd\":\"ping\"}",
            "{\"id\":01,\"cmd\":\"ping\"}",
            "{\"id\":9007199254740992,\"cmd\":\"ping\"}",
            "{\"id\":18446744073709551616,\"cmd\":\"ping\"}",
            "{\"id\":1,\"cmd\":[]}",
            "{\"id\":1,\"cmd\":{}}",
            "{\"id\":1,\"cmd\":true}",
            "{\"id\":1,\"cmd\":null}",
            "{\"id\":\"1\",\"cmd\":\"ping\"}",
            "{\"id\":1,\"cmd\":\"ping\",}",
            "{\"id\":1,\"cmd\":\"ping\"}junk",
            "{\"id\":1,\"cmd\":\"pi\\qng\"}",
            "{\"id\":1,\"cmd\":\"pi\\u0080ng\"}",
            "{\"id\":1,\"cmd\":\"pi\\uD800ng\"}",
            "{\"id\":1,\"cmd\":\"unknown\"}",
            "{\"id\":1,\"cmd\":\"set_input\",\"mask\":4096}",
            "{\"id\":1,\"cmd\":\"set_input\",\"mask\":1,\"port\":5}",
            "{\"id\":1,\"cmd\":\"set_input\"}",
            "{\"id\":1,\"cmd\":\"set_input\",\"mask\":\"1\"}",
            "{\"id\":1,\"cmd\":\"clear_input\",\"port\":5}",
            "{\"id\":1,\"cmd\":\"step_frames\",\"frames\":0}",
            "{\"id\":1,\"cmd\":\"step_frames\",\"frames\":601}",
            "{\"id\":1,\"cmd\":\"screenshot\",\"path\":\"out.png\"}",
            "{\"id\":1,\"cmd\":\"screenshot\",\"source\":\"bad\"}",
            "{\"id\":1,\"cmd\":\"present_shot\",\"source\":\"guest\"}"}) {
        require(has(peer.call(server, state, invalid), "\"ok\":false") &&
                    !server.quit_requested() &&
                    server.input_masks() == std::array<std::uint16_t, 5>{},
                "invalid request accepted or mutated state");
        ++checks;
      }
      auto missing = state;
      missing.capture = {};
      require(
          has(peer.call(server, missing, "{\"id\":1,\"cmd\":\"screenshot\"}"),
              "capture unavailable"),
          "unavailable capture accepted");
      ++checks;
      auto invalid = state;
      invalid.capture = [](bool) {
        return pce::VideoFrame{1025, 1, std::vector<std::uint8_t>(3075)};
      };
      require(
          has(peer.call(server, invalid, "{\"id\":1,\"cmd\":\"screenshot\"}"),
              "\"ok\":false"),
          "oversize guest image accepted");
      ++checks;
      invalid.capture = [](bool) { return pce::VideoFrame{2, 1, {1}}; };
      require(
          has(peer.call(server, invalid, "{\"id\":1,\"cmd\":\"screenshot\"}"),
              "\"ok\":false"),
          "malformed RGB accepted");
      ++checks;
      invalid.capture = [](bool) -> pce::VideoFrame {
        throw std::runtime_error("authored capture refusal");
      };
      require(
          has(peer.call(server, invalid, "{\"id\":1,\"cmd\":\"screenshot\"}"),
              "authored capture refusal"),
          "capture exception escaped server");
      ++checks;
      invalid = state;
      invalid.frame = std::numeric_limits<std::uint64_t>::max();
      require(has(peer.call(server, invalid,
                            "{\"id\":1,\"cmd\":\"step_frames\",\"frames\":1}"),
                  "\"ok\":false"),
              "frame target overflow accepted");
      ++checks;
      peer.call(server, state, "{\"id\":1,\"cmd\":\"set_input\",\"mask\":8}");
      peer.close();
      for (unsigned n = 0; n < 10; ++n)
        server.poll(state);
      require(server.input_masks()[0] == 0 && server.paused(12),
              "disconnect did not release input or lost pause");
      ++checks;
    }
    {
      Peer peer(server.port());
      require(has(peer.call(server, state, "{\"id\":99,\"cmd\":\"ping\"}"),
                  "\"id\":99,\"ok\":true"),
              "reconnection failed");
      ++checks;
      peer.send(std::string(8192, 'x'));
      require(has(peer.response(server, state), "request exceeds 8192 bytes"),
              "oversize request not bounded");
      ++checks;
    }
    for (unsigned n = 0; n < 10; ++n)
      server.poll(state);
    {
      Peer peer(server.port());
      peer.send("{");
      server.poll(state);
      std::this_thread::sleep_for(std::chrono::milliseconds(5100));
      server.poll(state);
      ++checks;
    }
    {
      Peer peer(server.port());
      auto large = state;
      large.capture = [](bool) {
        return pce::VideoFrame{2000, 2000,
                               std::vector<std::uint8_t>(12000000, 0x55)};
      };
      peer.send("{\"id\":101,\"cmd\":\"present_shot\"}\n");
      const auto begin = std::chrono::steady_clock::now();
      server.poll(large);
      require(std::chrono::steady_clock::now() - begin <
                  std::chrono::seconds(2),
              "large response blocked poll waiting for reader");
      ++checks;
      // Intentionally never drain this response. The absolute send deadline
      // must release it and permit another connection, without host changes.
      std::this_thread::sleep_for(std::chrono::milliseconds(5100));
      server.poll(state);
      require(server.paused(12) &&
                  server.input_masks() == std::array<std::uint16_t, 5>{},
              "stalled capture changed host controls");
      ++checks;
    }
    {
      Peer peer(server.port());
      require(has(peer.call(server, state, "{\"id\":100,\"cmd\":\"quit\"}"),
                  "\"ok\":true") &&
                  server.quit_requested(),
              "quit failed after stalled-client timeout");
      ++checks;
    }
    std::cout
        << checks
        << " development-server TCP/parser/control/capture checks passed\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
