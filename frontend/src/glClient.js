import { createClient } from 'genlayer-js'
import { studionet, testnetBradbury } from 'genlayer-js/chains'
import { TransactionStatus } from 'genlayer-js/types'
import { getNetwork } from './api'

const CONTRACTS = {
  studionet: '0xd55857A39092a80C16C152dffccF8098186BeAFF',
  bradbury: '0x6E7694c3ffbB4b109b2A37D009cE29425039E9da',
}

const CHAINS = {
  studionet,
  bradbury: testnetBradbury,
}

const CHAIN_NAMES = {
  studionet: 'studionet',
  bradbury: 'testnetBradbury',
}

export function getContractAddress(net) {
  return CONTRACTS[net || getNetwork()]
}

export function getChain(net) {
  return CHAINS[net || getNetwork()] || studionet
}

export function getChainName(net) {
  return CHAIN_NAMES[net || getNetwork()] || 'studionet'
}

export function createReadClient(net) {
  return createClient({ chain: getChain(net) })
}

export function createWriteClient(walletAddress, provider) {
  const net = getNetwork()
  return createClient({
    chain: getChain(net),
    account: walletAddress,
    provider: provider || window.ethereum,
  })
}

// ── Direct contract read (returns parsed JSON or null) ──
export async function contractRead(fn, args = []) {
  try {
    const client = createReadClient()
    const raw = await client.readContract({
      address: getContractAddress(),
      functionName: fn,
      args,
    })
    return typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch (e) {
    console.warn(`Contract read ${fn} failed:`, e.message)
    return null
  }
}

// ── Wallet-signed contract write (pops wallet popup) ──
export async function contractWrite(wallet, functionName, args, provider) {
  const p = provider || window.ethereum
  if (!p || !wallet) throw new Error('No wallet available')
  const client = createWriteClient(wallet, p)
  await client.connect(getChainName())
  const txHash = await client.writeContract({
    address: getContractAddress(),
    functionName,
    args,
    value: BigInt(0),
  })
  return client.waitForTransactionReceipt({
    hash: txHash,
    status: TransactionStatus.ACCEPTED,
  })
}
