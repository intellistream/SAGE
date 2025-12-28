#include <Utils/Meters/IntelMeter/IntelMeter.hpp>
#include <thread>

using namespace DIVERSE_METER;

IntelMeter::IntelMeter(/* args */) {
  //system("modprobe cpuid\r\n");
  //system("modprobe msr\r\n");

  //en=vector<double>(maxCpu);
}

void IntelMeter::setConfig(INTELLI::ConfigMapPtr _cfg) {
  AbstractMeter::setConfig(_cfg);
  maxCpu = std::thread::hardware_concurrency();
  power_units = get_rapl_power_unit();
  uint32_t i;
  //printf("we have %d ,%dcores\r\n",maxCpu,i);
  cpus = vector<int>(maxCpu);
  st = vector<double>(maxCpu);
  en = vector<double>(maxCpu);
  count = vector<double>(maxCpu);

  for (i = 0; i < maxCpu; i++) {
    cpus[i] = i;
  }
}

IntelMeter::~IntelMeter() {

}

uint64_t IntelMeter::rdmsr(int cpu, uint32_t reg) {
  char buf[1024];
  sprintf(buf, "/dev/cpu/%d/msr", cpu);
  int msr_file = open(buf, O_RDONLY);
  if (msr_file < 0) {
    perror("rdmsr: open");
    return msr_file;
  }
  uint64_t data;
  if (pread(msr_file, &data, sizeof(data), reg) != sizeof(data)) {
    fprintf(stderr, "read msr register 0x%x error.\n", reg);
    perror("rdmsr: read msr");
    return -1;
  }
  close(msr_file);
  return data;
}

rapl_power_unit IntelMeter::get_rapl_power_unit() {
  rapl_power_unit ret;
  uint64_t data = rdmsr(0, 0x606);
  double t = (1 << (data & 0xf));
  t = 1.0 / t;
  ret.PU = t;
  t = (1 << ((data >> 8) & 0x1f));
  ret.ESU = 1.0 / t;
  t = (1 << ((data >> 16) & 0xf));
  ret.TU = 1.0 / t;
  return ret;
}

void IntelMeter::startMeter() {
  double energy_units = power_units.ESU;
  uint32_t cpu, i;
  uint64_t data;
  size_t n = st.size();
  for (i = 0; i < n; ++i) {
    cpu = cpus[i];
    data = rdmsr(cpu, 0x611);
    st[i] = (data & 0xffffffff) * energy_units;
  }
}

void IntelMeter::stopMeter() {
  double energy_units = power_units.ESU;
  uint32_t cpu, i;
  uint64_t data;
  size_t n = st.size();
  eSum = 0;
  for (i = 0; i < n; ++i) {
    cpu = cpus[i];
    data = rdmsr(cpu, 0x611);
    en[i] = (data & 0xffffffff) * energy_units;
    count[i] = 0;
    if (en[i] < st[i]) {
      count[i] = (double) (1ll << 32) + en[i] - st[i];
    } else {
      count[i] = en[i] - st[i];
    }
    eSum += count[i];
  }

}

double IntelMeter::getE() {

  return eSum / 1000.0;
}

