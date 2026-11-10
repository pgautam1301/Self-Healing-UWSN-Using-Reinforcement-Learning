/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Energy-Efficient Depth-Based Routing (EEDBR) Protocol for Aqua-Sim NG
 * Reference: Abdul Wahid, Sungwon Lee, Hong-Jong Jeong, Dongkyun Kim,
 * "EEDBR: Energy-Efficient Depth-Based Routing Protocol for Underwater Wireless Sensor Networks",
 * Communications in Computer and Information Science (CCIS), Vol. 195, pp. 223-234, 2011.
 * DOI: 10.1007/978-3-642-24267-0_27
 */

#ifndef AQUA_SIM_ROUTING_EEDBR_H
#define AQUA_SIM_ROUTING_EEDBR_H

#include "aqua-sim-routing.h"
#include "aqua-sim-address.h"
#include "aqua-sim-header.h"
#include "aqua-sim-pt-tag.h"

#include "ns3/header.h"
#include "ns3/vector.h"
#include "ns3/timer.h"
#include "ns3/random-variable-stream.h"
#include "ns3/mobility-model.h"

#include <deque>
#include <map>
#include <vector>

namespace ns3 {

class AquaSimEEDBR;

/**
 * \brief EEDBR Packet Header carrying depth, energy and the forwarding node list.
 */
class EEDBRHeader : public Header
{
public:
  static const uint8_t MODE_DATA = 0;
  static const uint8_t MODE_BEACON = 1;
  static const uint8_t MAX_FWD_LIST = 4;

  EEDBRHeader();
  virtual ~EEDBRHeader();
  static TypeId GetTypeId(void);

  void SetPacketID(uint32_t packetID);
  uint32_t GetPacketID(void) const;

  void SetMode(uint8_t mode);
  uint8_t GetMode(void) const;

  void SetDepth(double depth);
  double GetDepth(void) const;

  void SetEnergy(double energy);
  double GetEnergy(void) const;

  void SetSender(AquaSimAddress sender);
  AquaSimAddress GetSender(void) const;

  void SetForwardingList(const std::vector<uint32_t>& list);
  std::vector<uint32_t> GetForwardingList(void) const;
  uint8_t GetForwardingCount(void) const;
  int GetPriority(uint32_t nodeId) const; // returns 0 for highest, 1 for 2nd, -1 if not in list

  virtual uint32_t GetSerializedSize(void) const;
  virtual void Serialize(Buffer::Iterator start) const;
  virtual uint32_t Deserialize(Buffer::Iterator start);
  virtual void Print(std::ostream &os) const;
  virtual TypeId GetInstanceTypeId(void) const;

private:
  uint32_t m_packetID;
  uint8_t m_mode;
  double m_depth;
  double m_energy;
  uint16_t m_senderAddr;
  uint8_t m_fwdCount;
  uint16_t m_fwdList[MAX_FWD_LIST];
};

/**
 * \brief Neighbor entry maintained during Knowledge Acquisition Phase (KAP).
 */
struct EEDBRNeighborEntry
{
  AquaSimAddress addr;
  double depth;        // z-coordinate
  double energy;       // residual energy in Joules
  Time lastSeen;
};

/**
 * \brief Item stored in the scheduled transmission queue.
 */
class QueueItemEEDBR
{
public:
  QueueItemEEDBR(Ptr<Packet> p, double sendTime, uint32_t pktId, int prio)
    : m_p(p), m_sendTime(sendTime), m_packetId(pktId), m_priority(prio) {}
  ~QueueItemEEDBR() { m_p = nullptr; }

  Ptr<Packet> m_p;
  double m_sendTime;
  uint32_t m_packetId;
  int m_priority;
};

/**
 * \brief Priority transmission queue ordered by scheduled departure time.
 */
class EEDBRPacketQueue
{
public:
  EEDBRPacketQueue();
  ~EEDBRPacketQueue();

  bool Empty() const { return m_dq.empty(); }
  size_t Size() const { return m_dq.size(); }

  void Insert(QueueItemEEDBR* q);
  QueueItemEEDBR* Front() { return m_dq.empty() ? nullptr : m_dq.front(); }
  void Pop();
  bool Purge(uint32_t packetId);
  bool Update(uint32_t packetId, double newSendTime);

private:
  std::deque<QueueItemEEDBR*> m_dq;
};

/**
 * \brief Timer for scheduled packet transmissions.
 */
class EEDBR_SendingTimer : public Timer
{
public:
  EEDBR_SendingTimer(AquaSimEEDBR *eedbr)
    : Timer(Timer::CANCEL_ON_DESTROY), m_eedbr(eedbr) {}
  virtual ~EEDBR_SendingTimer() {}
  void Expire();

private:
  AquaSimEEDBR *m_eedbr;
};

/**
 * \brief Timer for Knowledge Acquisition Phase (KAP) beaconing.
 */
class EEDBR_BeaconTimer : public Timer
{
public:
  EEDBR_BeaconTimer(AquaSimEEDBR *eedbr)
    : Timer(Timer::CANCEL_ON_DESTROY), m_eedbr(eedbr) {}
  virtual ~EEDBR_BeaconTimer() {}
  void Expire();

private:
  AquaSimEEDBR *m_eedbr;
};

/**
 * \brief Simple packet cache to avoid broadcast loops.
 */
class EEDBR_PacketCache
{
public:
  EEDBR_PacketCache(size_t maxSize = 500);
  ~EEDBR_PacketCache();

  bool AccessPacket(uint32_t pid);
  void AddPacket(uint32_t pid);

private:
  size_t m_maxSize;
  std::deque<uint32_t> m_cache;
};

/**
 * \brief Implementation of Energy-Efficient Depth-Based Routing (EEDBR).
 */
class AquaSimEEDBR : public AquaSimRouting
{
  friend class EEDBR_SendingTimer;
  friend class EEDBR_BeaconTimer;

public:
  static TypeId GetTypeId(void);
  AquaSimEEDBR();
  virtual ~AquaSimEEDBR();

  virtual bool Recv(Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber);
  int64_t AssignStreams(int64_t stream);

  void Send_Callback(void);
  void Beacon_Callback(void);

protected:
  virtual void DoDispose();

  void SendBeacon(void);
  void HandleBeacon(Ptr<Packet> p);
  void HandleDataPacket(Ptr<Packet> p);
  void ForwardPacket(Ptr<Packet> p);

  std::vector<uint32_t> SelectForwardingNodes(double myDepth);

private:
  double m_maxRange;          // Transmission range normalizer (default 250 m)
  double m_tMax;              // Maximum holding time scale (default 0.2 s)
  double m_priorityStep;      // Per-rank priority time offset (default 0.05 s)
  double m_beaconInterval;    // Periodic beacon interval (default 10.0 s)
  double m_initialEnergy;     // Initial reference energy (default 100.0 J)

  uint32_t m_pktCnt;          // Local originated packet counter
  double m_latest;            // Latest scheduled send time

  std::map<uint32_t, EEDBRNeighborEntry> m_neighbors; // Neighbor table (KAP)
  EEDBRPacketQueue m_pq;      // Transmission holding queue
  EEDBR_PacketCache m_pc;     // Sent/delivered packet history cache

  EEDBR_SendingTimer *m_sendTimer;
  EEDBR_BeaconTimer *m_beaconTimer;
  Ptr<UniformRandomVariable> m_rand;
};

} // namespace ns3

#endif /* AQUA_SIM_ROUTING_EEDBR_H */
