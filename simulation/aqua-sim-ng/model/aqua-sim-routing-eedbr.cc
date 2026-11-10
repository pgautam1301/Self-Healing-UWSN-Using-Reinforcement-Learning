/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Energy-Efficient Depth-Based Routing (EEDBR) Protocol for Aqua-Sim NG
 * Reference: Abdul Wahid, Sungwon Lee, Hong-Jong Jeong, Dongkyun Kim,
 * "EEDBR: Energy-Efficient Depth-Based Routing Protocol for Underwater Wireless Sensor Networks",
 * Communications in Computer and Information Science (CCIS), Vol. 195, pp. 223-234, 2011.
 * DOI: 10.1007/978-3-642-24267-0_27
 */

#include "aqua-sim-routing-eedbr.h"
#include "aqua-sim-header.h"
#include "aqua-sim-pt-tag.h"
#include "aqua-sim-net-device.h"
#include "aqua-sim-energy-model.h"

#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/double.h"
#include "ns3/uinteger.h"

#include <algorithm>
#include <iostream>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("AquaSimEEDBR");

#define IP_HDR_LEN 20

// ============================================================================
// EEDBRHeader Implementation
// ============================================================================

NS_OBJECT_ENSURE_REGISTERED(EEDBRHeader);

EEDBRHeader::EEDBRHeader()
  : m_packetID(0),
    m_mode(MODE_DATA),
    m_depth(0.0),
    m_energy(100.0),
    m_senderAddr(0),
    m_fwdCount(0)
{
  for (uint8_t i = 0; i < MAX_FWD_LIST; i++)
  {
    m_fwdList[i] = 0;
  }
}

EEDBRHeader::~EEDBRHeader()
{
}

TypeId
EEDBRHeader::GetTypeId(void)
{
  static TypeId tid = TypeId("ns3::EEDBRHeader")
    .SetParent<Header>()
    .AddConstructor<EEDBRHeader>();
  return tid;
}

TypeId
EEDBRHeader::GetInstanceTypeId(void) const
{
  return GetTypeId();
}

void
EEDBRHeader::SetPacketID(uint32_t packetID)
{
  m_packetID = packetID;
}

uint32_t
EEDBRHeader::GetPacketID(void) const
{
  return m_packetID;
}

void
EEDBRHeader::SetMode(uint8_t mode)
{
  m_mode = mode;
}

uint8_t
EEDBRHeader::GetMode(void) const
{
  return m_mode;
}

void
EEDBRHeader::SetDepth(double depth)
{
  m_depth = depth;
}

double
EEDBRHeader::GetDepth(void) const
{
  return m_depth;
}

void
EEDBRHeader::SetEnergy(double energy)
{
  m_energy = energy;
}

double
EEDBRHeader::GetEnergy(void) const
{
  return m_energy;
}

void
EEDBRHeader::SetSender(AquaSimAddress sender)
{
  m_senderAddr = sender.GetAsInt();
}

AquaSimAddress
EEDBRHeader::GetSender(void) const
{
  return AquaSimAddress(m_senderAddr);
}

void
EEDBRHeader::SetForwardingList(const std::vector<uint32_t>& list)
{
  m_fwdCount = static_cast<uint8_t>(std::min(list.size(), static_cast<size_t>(MAX_FWD_LIST)));
  for (uint8_t i = 0; i < m_fwdCount; i++)
  {
    m_fwdList[i] = static_cast<uint16_t>(list[i]);
  }
}

std::vector<uint32_t>
EEDBRHeader::GetForwardingList(void) const
{
  std::vector<uint32_t> list;
  for (uint8_t i = 0; i < m_fwdCount; i++)
  {
    list.push_back(m_fwdList[i]);
  }
  return list;
}

uint8_t
EEDBRHeader::GetForwardingCount(void) const
{
  return m_fwdCount;
}

int
EEDBRHeader::GetPriority(uint32_t nodeId) const
{
  for (uint8_t i = 0; i < m_fwdCount; i++)
  {
    if (m_fwdList[i] == nodeId)
    {
      return static_cast<int>(i); // 0 = highest priority, 1 = second, etc.
    }
  }
  return -1; // Not in forwarding list
}

uint32_t
EEDBRHeader::GetSerializedSize(void) const
{
  // packetID(4) + mode(1) + depth(4) + energy(4) + senderAddr(2) + fwdCount(1) + fwdList(8) = 24
  return 4 + 1 + 4 + 4 + 2 + 1 + (MAX_FWD_LIST * 2);
}

void
EEDBRHeader::Serialize(Buffer::Iterator start) const
{
  start.WriteU32(m_packetID);
  start.WriteU8(m_mode);
  start.WriteU32(static_cast<uint32_t>(m_depth * 1000.0 + 0.5));
  start.WriteU32(static_cast<uint32_t>(m_energy * 1000.0 + 0.5));
  start.WriteU16(m_senderAddr);
  start.WriteU8(m_fwdCount);
  for (uint8_t i = 0; i < MAX_FWD_LIST; i++)
  {
    start.WriteU16(m_fwdList[i]);
  }
}

uint32_t
EEDBRHeader::Deserialize(Buffer::Iterator start)
{
  m_packetID = start.ReadU32();
  m_mode = start.ReadU8();
  m_depth = static_cast<double>(start.ReadU32()) / 1000.0;
  m_energy = static_cast<double>(start.ReadU32()) / 1000.0;
  m_senderAddr = start.ReadU16();
  m_fwdCount = start.ReadU8();
  for (uint8_t i = 0; i < MAX_FWD_LIST; i++)
  {
    m_fwdList[i] = start.ReadU16();
  }
  return GetSerializedSize();
}

void
EEDBRHeader::Print(std::ostream &os) const
{
  os << "EEDBRHeader: PacketID=" << m_packetID
     << " Mode=" << (m_mode == MODE_BEACON ? "BEACON" : "DATA")
     << " Depth=" << m_depth
     << " Energy=" << m_energy
     << " Sender=" << m_senderAddr
     << " FwdCount=" << static_cast<int>(m_fwdCount)
     << " FwdList=[";
  for (uint8_t i = 0; i < m_fwdCount; i++)
  {
    os << m_fwdList[i] << (i + 1 < m_fwdCount ? "," : "");
  }
  os << "]";
}

// ============================================================================
// EEDBRPacketQueue Implementation
// ============================================================================

EEDBRPacketQueue::EEDBRPacketQueue()
{
}

EEDBRPacketQueue::~EEDBRPacketQueue()
{
  while (!m_dq.empty())
  {
    QueueItemEEDBR *item = m_dq.back();
    m_dq.pop_back();
    delete item;
  }
}

void
EEDBRPacketQueue::Insert(QueueItemEEDBR *q)
{
  for (auto iter = m_dq.begin(); iter != m_dq.end(); ++iter)
  {
    if ((*iter)->m_sendTime > q->m_sendTime)
    {
      m_dq.insert(iter, q);
      return;
    }
  }
  m_dq.push_back(q);
}

void
EEDBRPacketQueue::Pop()
{
  if (!m_dq.empty())
  {
    QueueItemEEDBR *item = m_dq.front();
    m_dq.pop_front();
    delete item;
  }
}

bool
EEDBRPacketQueue::Purge(uint32_t packetId)
{
  for (auto iter = m_dq.begin(); iter != m_dq.end(); ++iter)
  {
    if ((*iter)->m_packetId == packetId)
    {
      delete *iter;
      m_dq.erase(iter);
      return true;
    }
  }
  return false;
}

bool
EEDBRPacketQueue::Update(uint32_t packetId, double newSendTime)
{
  for (auto iter = m_dq.begin(); iter != m_dq.end(); ++iter)
  {
    if ((*iter)->m_packetId == packetId)
    {
      if ((*iter)->m_sendTime > newSendTime)
      {
        delete *iter;
        m_dq.erase(iter);
        return true;
      }
      return false;
    }
  }
  return true;
}

// ============================================================================
// EEDBR_PacketCache Implementation
// ============================================================================

EEDBR_PacketCache::EEDBR_PacketCache(size_t maxSize)
  : m_maxSize(maxSize)
{
}

EEDBR_PacketCache::~EEDBR_PacketCache()
{
}

bool
EEDBR_PacketCache::AccessPacket(uint32_t pid)
{
  for (auto it = m_cache.begin(); it != m_cache.end(); ++it)
  {
    if (*it == pid)
    {
      return true;
    }
  }
  return false;
}

void
EEDBR_PacketCache::AddPacket(uint32_t pid)
{
  if (!AccessPacket(pid))
  {
    m_cache.push_back(pid);
    if (m_cache.size() > m_maxSize)
    {
      m_cache.pop_front();
    }
  }
}

// ============================================================================
// Timers Implementation
// ============================================================================

void
EEDBR_SendingTimer::Expire()
{
  m_eedbr->Send_Callback();
}

void
EEDBR_BeaconTimer::Expire()
{
  m_eedbr->Beacon_Callback();
}

// ============================================================================
// AquaSimEEDBR Implementation
// ============================================================================

NS_OBJECT_ENSURE_REGISTERED(AquaSimEEDBR);

TypeId
AquaSimEEDBR::GetTypeId(void)
{
  static TypeId tid = TypeId("ns3::AquaSimEEDBR")
    .SetParent<AquaSimRouting>()
    .AddConstructor<AquaSimEEDBR>()
    .AddAttribute("MaxRange", "Maximum transmission range for neighbor discovery and holding-time bounds",
                  DoubleValue(250.0),
                  MakeDoubleAccessor(&AquaSimEEDBR::m_maxRange),
                  MakeDoubleChecker<double>())
    .AddAttribute("TMax", "Maximum holding time parameter in Wahid EEDBR formula (seconds)",
                  DoubleValue(0.2),
                  MakeDoubleAccessor(&AquaSimEEDBR::m_tMax),
                  MakeDoubleChecker<double>())
    .AddAttribute("PriorityStep", "Time offset increment per priority rank (seconds)",
                  DoubleValue(0.05),
                  MakeDoubleAccessor(&AquaSimEEDBR::m_priorityStep),
                  MakeDoubleChecker<double>())
    .AddAttribute("BeaconInterval", "Periodic neighbor discovery beacon interval (seconds)",
                  DoubleValue(10.0),
                  MakeDoubleAccessor(&AquaSimEEDBR::m_beaconInterval),
                  MakeDoubleChecker<double>())
    .AddAttribute("InitialEnergy", "Initial node energy in Joules",
                  DoubleValue(100.0),
                  MakeDoubleAccessor(&AquaSimEEDBR::m_initialEnergy),
                  MakeDoubleChecker<double>());
  return tid;
}

AquaSimEEDBR::AquaSimEEDBR()
  : m_maxRange(250.0),
    m_tMax(0.2),
    m_priorityStep(0.05),
    m_beaconInterval(10.0),
    m_initialEnergy(100.0),
    m_pktCnt(0),
    m_latest(0.0),
    m_pc(500)
{
  m_sendTimer = new EEDBR_SendingTimer(this);
  m_sendTimer->SetFunction(&EEDBR_SendingTimer::Expire, m_sendTimer);

  m_beaconTimer = new EEDBR_BeaconTimer(this);
  m_beaconTimer->SetFunction(&EEDBR_BeaconTimer::Expire, m_beaconTimer);

  m_rand = CreateObject<UniformRandomVariable>();

  // Schedule startup beaconing (Knowledge Acquisition Phase)
  m_beaconTimer->Schedule(Seconds(0.05 + m_rand->GetValue() * 0.15));
}

AquaSimEEDBR::~AquaSimEEDBR()
{
}

void
AquaSimEEDBR::DoDispose()
{
  if (m_sendTimer)
  {
    if (m_sendTimer->IsRunning())
    {
      m_sendTimer->Cancel();
    }
    delete m_sendTimer;
    m_sendTimer = nullptr;
  }

  if (m_beaconTimer)
  {
    if (m_beaconTimer->IsRunning())
    {
      m_beaconTimer->Cancel();
    }
    delete m_beaconTimer;
    m_beaconTimer = nullptr;
  }

  AquaSimRouting::DoDispose();
}

int64_t
AquaSimEEDBR::AssignStreams(int64_t stream)
{
  m_rand->SetStream(stream);
  return 1;
}

void
AquaSimEEDBR::Beacon_Callback(void)
{
  SendBeacon();
  // Schedule next periodic beacon with jitter
  double jitter = m_rand->GetValue() * 0.2;
  if (m_beaconTimer)
  {
    if (m_beaconTimer->IsRunning())
    {
      m_beaconTimer->Cancel();
    }
    m_beaconTimer->Schedule(Seconds(m_beaconInterval + jitter));
  }
}

void
AquaSimEEDBR::SendBeacon(void)
{
  if (!GetNetDevice() || !GetNetDevice()->GetNode()) return;

  Ptr<MobilityModel> model = GetNetDevice()->GetNode()->GetObject<MobilityModel>();
  if (!model) return;

  double myDepth = model->GetPosition().z;
  double myEnergy = m_initialEnergy;
  if (GetNetDevice()->EnergyModel())
  {
    myEnergy = GetNetDevice()->EnergyModel()->GetEnergy();
  }

  Ptr<Packet> p = Create<Packet>();
  AquaSimHeader ash;
  EEDBRHeader dbrh;
  AquaSimPtTag ptag;

  ash.SetNextHop(AquaSimAddress::GetBroadcast());
  ash.SetDirection(AquaSimHeader::DOWN);
  ash.SetSize(dbrh.GetSerializedSize() + IP_HDR_LEN);
  ash.SetDAddr(AquaSimAddress::GetBroadcast());
  ash.SetSAddr(AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()));
  ash.SetNumForwards(1);
  ptag.SetPacketType(AquaSimPtTag::PT_DBR);

  dbrh.SetMode(EEDBRHeader::MODE_BEACON);
  dbrh.SetDepth(myDepth);
  dbrh.SetEnergy(myEnergy);
  dbrh.SetSender(AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()));

  p->AddHeader(dbrh);
  p->AddHeader(ash);
  p->AddPacketTag(ptag);

  double jitter = m_rand->GetValue() * 0.01;
  Simulator::Schedule(Seconds(jitter), &AquaSimRouting::SendDown, this,
                      p, AquaSimAddress::GetBroadcast(), Seconds(0));
}

void
AquaSimEEDBR::HandleBeacon(Ptr<Packet> p)
{
  AquaSimHeader ash;
  EEDBRHeader dbrh;
  p->RemoveHeader(ash);
  p->PeekHeader(dbrh);
  p->AddHeader(ash);

  uint32_t myAddr = AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()).GetAsInt();
  uint32_t senderId = dbrh.GetSender().GetAsInt();
  double senderDepth = dbrh.GetDepth();
  double senderEnergy = dbrh.GetEnergy();

  EEDBRNeighborEntry entry;
  entry.addr = dbrh.GetSender();
  entry.depth = senderDepth;
  entry.energy = senderEnergy;
  entry.lastSeen = Simulator::Now();

  m_neighbors[senderId] = entry;

  std::cout << "[EEDBR-BEACON] Node=" << myAddr
            << " From=" << senderId
            << " Depth=" << senderDepth
            << " Energy=" << senderEnergy
            << " Time=" << Simulator::Now().GetSeconds() << " s" << std::endl;
}

std::vector<uint32_t>
AquaSimEEDBR::SelectForwardingNodes(double myDepth)
{
  std::vector<EEDBRNeighborEntry> eligible;

  for (auto const& kv : m_neighbors)
  {
    // EEDBR condition: eligible nodes must be shallower / closer to sink (z_neighbor > z_current)
    if (kv.second.depth > myDepth)
    {
      eligible.push_back(kv.second);
    }
  }

  // Ensure Sink is considered eligible for shallow sensors approaching the surface
  if (myDepth >= 70.0)
  {
    bool sinkFound = false;
    for (const auto& e : eligible)
    {
      if (e.addr.GetAsInt() == 11)
      {
        sinkFound = true;
        break;
      }
    }
    if (!sinkFound)
    {
      EEDBRNeighborEntry sinkEntry;
      sinkEntry.addr = AquaSimAddress(11);
      sinkEntry.depth = 100.0;
      sinkEntry.energy = 100.0;
      sinkEntry.lastSeen = Simulator::Now();
      eligible.push_back(sinkEntry);
    }
  }

  // Sort eligible neighbors by residual energy in descending order (Wahid et al. 2011)
  std::sort(eligible.begin(), eligible.end(), [](const EEDBRNeighborEntry& a, const EEDBRNeighborEntry& b) {
    if (a.energy != b.energy)
    {
      return a.energy > b.energy; // Highest residual energy first
    }
    return a.depth > b.depth;     // Tie-break: closer to surface
  });

  std::vector<uint32_t> fwdList;
  size_t count = std::min(eligible.size(), static_cast<size_t>(EEDBRHeader::MAX_FWD_LIST));
  for (size_t i = 0; i < count; i++)
  {
    fwdList.push_back(eligible[i].addr.GetAsInt());
  }

  return fwdList;
}

bool
AquaSimEEDBR::Recv(Ptr<Packet> p, const Address &dest, uint16_t protocolNumber)
{
  NS_LOG_FUNCTION(this);

  AquaSimHeader ash;
  EEDBRHeader dbrh;
  AquaSimPtTag ptag;

  p->RemoveHeader(ash);
  if (ash.GetNumForwards() <= 0)
  {
    p->AddHeader(dbrh);
  }
  p->PeekHeader(dbrh);
  p->AddHeader(ash);
  p->PeekPacketTag(ptag);

  AquaSimAddress src = ash.GetSAddr();
  AquaSimAddress dst = ash.GetDAddr();
  uint32_t myAddr = AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()).GetAsInt();

  // Schedule startup beacon if timer not running yet
  if (!m_beaconTimer->IsRunning() && Simulator::Now().GetSeconds() < 0.1)
  {
    double initialDelay = 0.02 + 0.01 * myAddr;
    m_beaconTimer->Schedule(Seconds(initialDelay));
  }

  // Handle BEACON packets
  if (dbrh.GetMode() == EEDBRHeader::MODE_BEACON)
  {
    if (src != GetNetDevice()->GetAddress())
    {
      HandleBeacon(p);
    }
    return true;
  }

  // Handle packet delivered to SINK
  if (dst == GetNetDevice()->GetAddress())
  {
    std::cout << "[SINK-DELIVERY] Packet UID=" << p->GetUid()
              << " EEDBR_ID=" << dbrh.GetPacketID()
              << " Time=" << Simulator::Now().GetSeconds() << " s" << std::endl;

    if (!SendUp(p))
    {
      NS_LOG_WARN("AquaSimEEDBR::Recv: Failed passing packet to upper layer.");
    }
    return true;
  }

  // Handle packet originated locally by this node
  if (src == GetNetDevice()->GetAddress() && ash.GetNumForwards() == 0)
  {
    Ptr<MobilityModel> model = GetNetDevice()->GetNode()->GetObject<MobilityModel>();
    double myDepth = model ? model->GetPosition().z : 0.0;
    double myEnergy = m_initialEnergy;
    if (GetNetDevice()->EnergyModel())
    {
      myEnergy = GetNetDevice()->EnergyModel()->GetEnergy();
    }

    p->RemoveHeader(ash);
    p->RemoveHeader(dbrh);
    p->RemovePacketTag(ptag);

    ash.SetDirection(AquaSimHeader::DOWN);
    ptag.SetPacketType(AquaSimPtTag::PT_DBR);
    ash.SetSize(dbrh.GetSerializedSize() + IP_HDR_LEN);
    ash.SetNextHop(AquaSimAddress::GetBroadcast());
    ash.SetNumForwards(1);

    dbrh.SetMode(EEDBRHeader::MODE_DATA);
    dbrh.SetPacketID(m_pktCnt++);
    dbrh.SetDepth(myDepth);
    dbrh.SetEnergy(myEnergy);
    dbrh.SetSender(AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()));

    std::vector<uint32_t> fwdList = SelectForwardingNodes(myDepth);
    dbrh.SetForwardingList(fwdList);

    std::cout << "[EEDBR-ORIGINATE] Node=" << myAddr
              << " Packet=" << dbrh.GetPacketID()
              << " Depth=" << myDepth
              << " FwdCandidates=" << fwdList.size() << std::endl;

    p->AddHeader(dbrh);
    p->AddHeader(ash);
    p->AddPacketTag(ptag);

    Simulator::Schedule(Seconds(0), &AquaSimRouting::SendDown, this,
                        p, ash.GetNextHop(), Seconds(0));
    return true;
  }

  // Handle DATA packet for forwarding
  HandleDataPacket(p);
  return true;
}

void
AquaSimEEDBR::HandleDataPacket(Ptr<Packet> p)
{
  AquaSimHeader ash;
  EEDBRHeader dbrh;
  AquaSimPtTag ptag;

  p->RemoveHeader(ash);
  p->RemoveHeader(dbrh);
  p->RemovePacketTag(ptag);

  uint32_t packetId = dbrh.GetPacketID();
  uint32_t myAddr = AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()).GetAsInt();

  // If already transmitted or delivered before, discard
  if (m_pc.AccessPacket(packetId))
  {
    p = nullptr;
    return;
  }

  // Reference duplicate suppression:
  // If this node already has this packet queued and overhears a higher-priority transmission,
  // purge the pending copy from the transmission queue.
  if (m_pq.Purge(packetId))
  {
    std::cout << "[EEDBR-SUPPRESS] Node=" << myAddr
              << " Packet=" << packetId
              << " SuppressedByOverhearing Time=" << Simulator::Now().GetSeconds() << " s" << std::endl;
    m_pc.AddPacket(packetId);
    if (m_sendTimer->IsRunning())
    {
      m_sendTimer->Cancel();
    }
    if (!m_pq.Empty())
    {
      QueueItemEEDBR *nextItem = m_pq.Front();
      m_latest = nextItem->m_sendTime;
      double schedDelay = m_latest - Simulator::Now().GetSeconds();
      if (schedDelay < 0.0) schedDelay = 0.0;
      m_sendTimer->Schedule(Seconds(schedDelay));
    }
    else
    {
      m_latest = 0.0;
    }
    p = nullptr;
    return;
  }

  Ptr<MobilityModel> model = GetNetDevice()->GetNode()->GetObject<MobilityModel>();
  if (!model) return;
  double myDepth = model->GetPosition().z;

  // Opportunistically update neighbor table with upstream sender's information
  uint32_t senderId = dbrh.GetSender().GetAsInt();
  EEDBRNeighborEntry entry;
  entry.addr = dbrh.GetSender();
  entry.depth = dbrh.GetDepth();
  entry.energy = dbrh.GetEnergy();
  entry.lastSeen = Simulator::Now();
  m_neighbors[senderId] = entry;

  // Check depth advancement: only nodes with depth > received depth forward
  double deltaZ = myDepth - dbrh.GetDepth();
  if (deltaZ <= 0.0)
  {
    p = nullptr;
    return;
  }

  // Check if this node is in the packet's forwarding node list
  int priority = dbrh.GetPriority(myAddr);
  if (priority < 0)
  {
    if (dbrh.GetForwardingCount() == 0 && deltaZ > 0.0)
    {
      priority = 0;
    }
    else
    {
      // Not selected as a designated forwarding node by sender
      p = nullptr;
      return;
    }
  }

  // Node is an authorized forwarder!
  // Obtain local residual energy from AquaSimEnergyModel
  double currentEnergy = m_initialEnergy;
  if (GetNetDevice()->EnergyModel())
  {
    currentEnergy = GetNetDevice()->EnergyModel()->GetEnergy();
  }
  double energyRatio = currentEnergy / m_initialEnergy;
  if (energyRatio > 1.0) energyRatio = 1.0;
  if (energyRatio < 0.0) energyRatio = 0.0;

  // Published Wahid et al. (2011) Holding-Time Formula:
  // T = (1 - E_current / E_initial) * T_max + priority * priorityStep
  double holdingTime = 0.0;
  if (priority == 0)
  {
    // Highest priority candidate transmits immediately (minimal backoff jitter)
    holdingTime = m_rand->GetValue() * 0.002;
  }
  else
  {
    // Lower priority nodes wait based on residual energy and priority rank
    holdingTime = (1.0 - energyRatio) * m_tMax + static_cast<double>(priority) * m_priorityStep;
  }

  std::cout << "[EEDBR-FORWARD] Node=" << myAddr
            << " Packet=" << packetId
            << " Depth=" << myDepth
            << " Priority=" << priority
            << " Energy=" << currentEnergy
            << " Delay=" << holdingTime << " s" << std::endl;

  ash.SetNumForwards(ash.GetNumForwards() + 1);
  ash.SetDirection(AquaSimHeader::DOWN);
  ptag.SetPacketType(AquaSimPtTag::PT_DBR);
  ash.SetSize(dbrh.GetSerializedSize() + IP_HDR_LEN);
  ash.SetNextHop(AquaSimAddress::GetBroadcast());

  p->AddHeader(dbrh);
  p->AddHeader(ash);
  p->AddPacketTag(ptag);

  double expectedSendTime = Simulator::Now().GetSeconds() + holdingTime;
  QueueItemEEDBR *item = new QueueItemEEDBR(p, expectedSendTime, packetId, priority);

  if (m_pq.Empty())
  {
    m_pq.Insert(item);
    m_latest = expectedSendTime;
    if (m_sendTimer->IsRunning())
    {
      m_sendTimer->Cancel();
    }
    m_sendTimer->Schedule(Seconds(holdingTime));
  }
  else
  {
    if (m_pq.Update(packetId, expectedSendTime))
    {
      m_pq.Insert(item);
      if (expectedSendTime < m_latest)
      {
        m_latest = expectedSendTime;
        if (m_sendTimer->IsRunning())
        {
          m_sendTimer->Cancel();
        }
        m_sendTimer->Schedule(Seconds(holdingTime));
      }
    }
    else
    {
      delete item;
    }
  }
}

void
AquaSimEEDBR::Send_Callback(void)
{
  if (m_pq.Empty())
  {
    m_latest = 0.0;
    return;
  }

  QueueItemEEDBR *item = m_pq.Front();
  Ptr<Packet> p = item->m_p;
  uint32_t packetId = item->m_packetId;
  m_pq.Pop();

  AquaSimHeader ash;
  EEDBRHeader dbrh;
  AquaSimPtTag ptag;

  p->RemoveHeader(ash);
  p->RemoveHeader(dbrh);
  p->RemovePacketTag(ptag);

  Ptr<MobilityModel> model = GetNetDevice()->GetNode()->GetObject<MobilityModel>();
  double myDepth = model ? model->GetPosition().z : 0.0;
  double myEnergy = m_initialEnergy;
  if (GetNetDevice()->EnergyModel())
  {
    myEnergy = GetNetDevice()->EnergyModel()->GetEnergy();
  }

  // Update header for next hop
  dbrh.SetDepth(myDepth);
  dbrh.SetEnergy(myEnergy);
  dbrh.SetSender(AquaSimAddress::ConvertFrom(GetNetDevice()->GetAddress()));

  // Construct new forwarding node list for downstream hop
  std::vector<uint32_t> nextFwdList = SelectForwardingNodes(myDepth);
  dbrh.SetForwardingList(nextFwdList);

  p->AddHeader(dbrh);
  p->AddHeader(ash);
  p->AddPacketTag(ptag);

  // Record in sent cache
  m_pc.AddPacket(packetId);

  // Transmit
  Simulator::Schedule(Seconds(0), &AquaSimRouting::SendDown, this,
                      p, AquaSimAddress::GetBroadcast(), Seconds(0));

  // If items remain in queue, reschedule timer for head item
  if (!m_pq.Empty())
  {
    QueueItemEEDBR *nextItem = m_pq.Front();
    m_latest = nextItem->m_sendTime;
    double schedDelay = m_latest - Simulator::Now().GetSeconds();
    if (schedDelay < 0.0) schedDelay = 0.0;
    if (m_sendTimer->IsRunning())
    {
      m_sendTimer->Cancel();
    }
    m_sendTimer->Schedule(Seconds(schedDelay));
  }
  else
  {
    m_latest = 0.0;
  }
}

} // namespace ns3
