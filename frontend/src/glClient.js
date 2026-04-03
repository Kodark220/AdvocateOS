import { createClient } from 'genlayer-js'
import { studionet, testnetBradbury } from 'genlayer-js/chains'
import { TransactionStatus } from 'genlayer-js/types'
import { getNetwork } from './api'

const CONTRACTS = {
  studionet: '0xA3C49D3B40EB3d4943812ED5B12BaB7FF1DEAeCe',
  bradbury: '0x2e75bc5796791b20b645b17dcf2a9dfc052c83ab',
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

// ── Switch chain on a specific provider (bypasses genlayer-js's MetaMask-only connect) ──
export async function switchChain(provider) {
  if (!provider) throw new Error('No wallet provider available')
  const chain = getChain()
  const chainIdHex = `0x${chain.id.toString(16)}`

  const currentChainId = await provider.request({ method: 'eth_chainId' })
  if (currentChainId !== chainIdHex) {
    try {
      await provider.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: chainIdHex }],
      })
    } catch (switchErr) {
      // 4902 = chain not added yet
      if (switchErr.code === 4902 || switchErr.message?.includes('Unrecognized chain')) {
        await provider.request({
          method: 'wallet_addEthereumChain',
          params: [{
            chainId: chainIdHex,
            chainName: chain.name,
            rpcUrls: chain.rpcUrls.default.http,
            nativeCurrency: chain.nativeCurrency,
            blockExplorerUrls: [chain.blockExplorers?.default?.url].filter(Boolean),
          }],
        })
      } else {
        throw switchErr
      }
    }
  }
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
  await switchChain(p)
  const client = createWriteClient(wallet, p)
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
