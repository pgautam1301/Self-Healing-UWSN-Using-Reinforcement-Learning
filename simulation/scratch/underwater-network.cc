
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/energy-module.h"
#include "ns3/aqua-sim-ng-module.h"
#include "ns3/applications-module.h"

using namespace ns3;

void FailSensor(Ptr<AquaSimNetDevice> device)
{
    device->SetAttribute("SetFailureStatus", BooleanValue(true));

    std::cout << "\n*** SENSOR FAILURE ***"
              << "\nSensor 5 has failed at "
              << Simulator::Now().GetSeconds()
              << " seconds\n";
}

void SourceTx(Ptr<const Packet> packet)
{
    std::cout << "[SOURCE-TX] Packet UID=" << packet->GetUid()
              << " Size=" << packet->GetSize()
              << " Time=" << Simulator::Now().GetSeconds() << " s\n";
}

void SinkRx(Ptr<Socket> socket)
{
    Ptr<Packet> packet;
    Address from;
    while ((packet = socket->RecvFrom(from)))
    {
        std::cout << "[SINK-DELIVERY] Packet UID=" << packet->GetUid()
                  << " Size=" << packet->GetSize()
                  << " Time=" << Simulator::Now().GetSeconds() << " s\n";
    }
}

NS_LOG_COMPONENT_DEFINE("UnderwaterNetwork");

int main(int argc, char *argv[])
{
    uint32_t nodes = 10;
    uint32_t sinks = 1;

    double simStop = 100;
    double range = 250;

    uint32_t dataRate = 1000;
    uint32_t packetSize = 40;
    uint32_t runNumber = 1;
    std::string routing = "VBF";

    CommandLine cmd;
    cmd.AddValue("nodes", "Number of sensor nodes", nodes);
    cmd.AddValue("simStop", "Simulation duration", simStop);
    cmd.AddValue("runNumber", "Random run number", runNumber);
    cmd.AddValue("routing", "Routing protocol (VBF, DBR, or EEDBR)", routing);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(runNumber);

    std::cout << "\n--- Initializing Underwater Network ---\n";

    NodeContainer nodesCon;
    NodeContainer sinksCon;
    NodeContainer senderCon;

    nodesCon.Create(nodes);
    sinksCon.Create(sinks);
    senderCon.Create(1);

    PacketSocketHelper socketHelper;
    socketHelper.Install(nodesCon);
    socketHelper.Install(sinksCon);
    socketHelper.Install(senderCon);

    AquaSimChannelHelper channel =
        AquaSimChannelHelper::Default();

    channel.SetPropagation(
        "ns3::AquaSimRangePropagation");

    AquaSimHelper asHelper =
        AquaSimHelper::Default();

    asHelper.SetChannel(channel.Create());

    asHelper.SetMac(
        "ns3::AquaSimBroadcastMac");
    // Configure Aqua-Sim energy model
    asHelper.SetEnergyModel(
	 "ns3::AquaSimEnergyModel",
	 "RxPower", DoubleValue(0.75),
	 "TxPower", DoubleValue(2.0),
	 "InitialEnergy", DoubleValue(100.0),
	 "IdlePower", DoubleValue(0.008));

    if (routing == "DBR")
    {
        asHelper.SetRouting("ns3::AquaSimDBR",
                            "MaxRange", DoubleValue(range));
    }
    else if (routing == "EEDBR")
    {
        asHelper.SetRouting("ns3::AquaSimEEDBR",
                            "MaxRange", DoubleValue(range),
                            "TMax", DoubleValue(0.2),
                            "PriorityStep", DoubleValue(0.05),
                            "InitialEnergy", DoubleValue(100.0));
    }
    else
    {
        asHelper.SetRouting(
            "ns3::AquaSimVBF",
            "Width", DoubleValue(100),
            "TargetPos",
            Vector3DValue(Vector(500, 500, 100)));
    }

    NetDeviceContainer devices;

    // Create underwater sensor devices
    for (NodeContainer::Iterator i = nodesCon.Begin();
         i != nodesCon.End(); ++i)
    {
        Ptr<AquaSimNetDevice> device =
            CreateObject<AquaSimNetDevice>();

        devices.Add(asHelper.Create(*i, device));

        device->GetPhy()->SetTransRange(range);
    }

    // Create sink device
    Ptr<AquaSimNetDevice> sinkDevice =
        CreateObject<AquaSimNetDevice>();

    devices.Add(asHelper.Create(sinksCon.Get(0), sinkDevice));

    sinkDevice->GetPhy()->SetTransRange(range);

    // Create sender device
    Ptr<AquaSimNetDevice> senderDevice =
        CreateObject<AquaSimNetDevice>();

    devices.Add(asHelper.Create(senderCon.Get(0), senderDevice));

    senderDevice->GetPhy()->SetTransRange(range);

    // Assign positions using reflected Z-axis: z_new = 100 - z_old
    MobilityHelper mobility;

    Ptr<ListPositionAllocator> sinkPosition =
        CreateObject<ListPositionAllocator>();

    sinkPosition->Add(Vector(500, 500, 100));

    mobility.SetPositionAllocator(sinkPosition);
    mobility.SetMobilityModel(
        "ns3::ConstantPositionMobilityModel");

    mobility.Install(sinksCon);

    Ptr<ListPositionAllocator> senderPosition =
        CreateObject<ListPositionAllocator>();

    senderPosition->Add(Vector(50, 50, 0));

    mobility.SetPositionAllocator(senderPosition);
    mobility.Install(senderCon);

    Ptr<ListPositionAllocator> nodePosition =
        CreateObject<ListPositionAllocator>();

    for (uint32_t i = 0; i < nodes; i++)
    {
        double x = 90 + i * 40;
        double y = 90 + i * 40;
        double z = 10 + i * 8;

        nodePosition->Add(Vector(x, y, z));
    }

    mobility.SetPositionAllocator(nodePosition);
    mobility.Install(nodesCon);

    // Configure source application
    PacketSocketAddress socket;
    socket.SetAllDevices();

    socket.SetPhysicalAddress(
        devices.Get(nodes)->GetAddress());

    socket.SetProtocol(0);

    OnOffHelper app(
        "ns3::PacketSocketFactory",
        Address(socket));

    app.SetAttribute(
        "OnTime",
        StringValue(
            "ns3::ConstantRandomVariable[Constant=1.0]"));

    app.SetAttribute(
        "OffTime",
        StringValue(
            "ns3::ConstantRandomVariable[Constant=0.0]"));

    app.SetAttribute(
        "DataRate",
        DataRateValue(dataRate));

    app.SetAttribute(
        "PacketSize",
        UintegerValue(packetSize));

    ApplicationContainer apps =
        app.Install(senderCon);

    apps.Start(Seconds(0.5));
    apps.Stop(Seconds(simStop));
    apps.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&SourceTx));

    Ptr<Socket> sinkSocket =
        Socket::CreateSocket(
            sinksCon.Get(0),
            TypeId::LookupByName(
                "ns3::PacketSocketFactory"));

    sinkSocket->Bind(socket);
    sinkSocket->SetRecvCallback(MakeCallback(&SinkRx));

    std::cout << "Sensor nodes created: " << nodes << "\n";
    std::cout << "Sink nodes created: " << sinks << "\n";
    std::cout << "Transmission range: " << range << " m\n";

    std::cout << "--- Running Simulation ---\n";

    Simulator::Stop(Seconds(simStop));
    // Schedule Sensor 5 failure at 50 seconds
    Ptr<AquaSimNetDevice> failedDevice =
        DynamicCast<AquaSimNetDevice>(devices.Get(4));

    Simulator::Schedule(
    	Seconds(50.0),
    	&FailSensor,
    	failedDevice);
    Simulator::Run();
    // Display energy consumption of sensor nodes
    std::cout << "\n--- Sensor Energy Report ---\n";

    for (uint32_t i = 0; i < nodes; i++)
    {
    Ptr<AquaSimNetDevice> device =
        DynamicCast<AquaSimNetDevice>(devices.Get(i));

    Ptr<AquaSimEnergyModel> energy =
        device->EnergyModel();

    double initial = energy->GetInitialEnergy();
    double remaining = energy->GetEnergy();
    double consumed = initial - remaining;

    std::cout << "Sensor " << i + 1
              << " | Initial Energy: " << initial << " J"
              << " | Remaining Energy: " << remaining << " J"
              << " | Consumed Energy: " << consumed << " J"
              << std::endl;}

    asHelper.GetChannel()->PrintCounters();

    Simulator::Destroy();

    std::cout << "--- Simulation Completed ---\n";

    return 0;
}
